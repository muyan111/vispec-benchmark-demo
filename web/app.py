# -*- coding: utf-8 -*-
import json
import os
import shlex
import subprocess
import threading
import time
import uuid
import webbrowser
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = WEB_ROOT / "static"
RUN_ROOT = REPO_ROOT / "web_runs"
RUN_ROOT.mkdir(parents=True, exist_ok=True)

SSH_PORT = os.environ.get("VISPEC_SSH_PORT", "2225")
SSH_HOST = os.environ.get("VISPEC_SSH_HOST", "root@localhost")
SSH_KEY = Path(
    os.path.expandvars(
        os.environ.get("VISPEC_SSH_KEY", r"%USERPROFILE%\.ssh\vispec_codex")
    )
).expanduser()
KNOWN_HOSTS = Path(
    os.path.expandvars(
        os.environ.get(
            "VISPEC_KNOWN_HOSTS", r"%USERPROFILE%\.ssh\vispec_node00_known_hosts"
        )
    )
).expanduser()
REMOTE_ROOT = os.environ.get("VISPEC_REMOTE_ROOT", "/home/vispec_repro")
REMOTE_PYTHON = os.environ.get(
    "VISPEC_REMOTE_PYTHON", "/root/miniconda3/envs/rekv/bin/python"
)
REMOTE_SCRIPT = os.environ.get(
    "VISPEC_REMOTE_SCRIPT", "/home/vispec_repro/run_benchmark.py"
)
MAX_UPLOAD_BYTES = int(os.environ.get("VISPEC_MAX_UPLOAD_BYTES", str(8 * 1024**3)))
VIDEO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}

app = FastAPI(title="ViSpec Experiment Console")
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

jobs = {}
jobs_lock = threading.Lock()


def now_iso():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def process_flags():
    return subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def ssh_base():
    return [
        "ssh",
        "-i",
        str(SSH_KEY),
        "-p",
        SSH_PORT,
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"UserKnownHostsFile={KNOWN_HOSTS}",
        SSH_HOST,
    ]


def scp_base():
    return [
        "scp",
        "-O",
        "-i",
        str(SSH_KEY),
        "-P",
        SSH_PORT,
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=10",
        "-o",
        "StrictHostKeyChecking=no",
        "-o",
        f"UserKnownHostsFile={KNOWN_HOSTS}",
    ]


def run_capture(command, timeout=30):
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        creationflags=process_flags(),
    )


def connection_status():
    if not SSH_KEY.is_file():
        return {
            "connected": False,
            "message": f"SSH key not found: {SSH_KEY}",
        }
    try:
        result = run_capture(
            ssh_base()
            + [
                "printf 'VISPEC_READY\\n'; hostname; test -f "
                + shlex.quote(REMOTE_SCRIPT)
                + " && printf 'SCRIPT_READY\\n'",
            ],
            timeout=12,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return {"connected": False, "message": str(exc)}

    connected = result.returncode == 0 and "VISPEC_READY" in result.stdout
    script_ready = "SCRIPT_READY" in result.stdout
    output = (result.stdout + result.stderr).strip()
    if not connected and ("Connection refused" in output or "connect to host" in output):
        output = f"Reverse tunnel is unavailable on localhost:{SSH_PORT}"
    return {
        "connected": connected,
        "script_ready": script_ready,
        "message": output or f"SSH exited with code {result.returncode}",
    }


def snapshot_job(job):
    snapshot = {key: value for key, value in job.items() if not key.startswith("_")}
    if snapshot.get("status") == "running" and snapshot.get("started_at_epoch"):
        duration_seconds = max(snapshot.get("duration_minutes", 0.1) * 60, 1)
        elapsed = time.time() - snapshot["started_at_epoch"]
        snapshot["progress"] = min(96, max(snapshot.get("progress", 0), int(elapsed / duration_seconds * 94)))
    return snapshot


def get_job(job_id):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")
        return job


def update_job(job_id, **values):
    with jobs_lock:
        job = jobs[job_id]
        job.update(values)
        snapshot = snapshot_job(job)
    state_path = Path(job["local_dir"]) / "state.json"
    state_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")


def append_log(job_id, line):
    with jobs_lock:
        job = jobs[job_id]
        job["log"] = (job.get("log", "") + line)[-300000:]


def stream_process(job_id, command):
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        bufsize=1,
        creationflags=process_flags(),
    )
    with jobs_lock:
        jobs[job_id]["_process"] = process
    assert process.stdout is not None
    for line in process.stdout:
        append_log(job_id, line)
    return_code = process.wait()
    with jobs_lock:
        jobs[job_id].pop("_process", None)
    return return_code


def remote_job(job_id):
    job = get_job(job_id)
    local_dir = Path(job["local_dir"])
    video_path = Path(job["video_path"])
    remote_job_dir = f"{REMOTE_ROOT}/web_jobs/{job_id}"
    remote_output_dir = f"{remote_job_dir}/output"
    remote_video = f"{remote_job_dir}/input{video_path.suffix.lower()}"

    try:
        update_job(job_id, status="checking", message="正在检查 A100 连接", progress=3)
        health = connection_status()
        if not health.get("connected"):
            raise RuntimeError("A100 connection unavailable: " + health.get("message", "unknown error"))
        if not health.get("script_ready"):
            raise RuntimeError(f"Server runner is missing: {REMOTE_SCRIPT}")

        update_job(job_id, status="uploading", message="正在上传视频到 A100", progress=8)
        mkdir_result = run_capture(
            ssh_base() + [f"mkdir -p {shlex.quote(remote_output_dir)}"], timeout=30
        )
        if mkdir_result.returncode != 0:
            raise RuntimeError(mkdir_result.stderr.strip() or "Failed to create remote directory")

        upload_result = run_capture(
            scp_base() + [str(video_path), f"{SSH_HOST}:{remote_video}"],
            timeout=max(300, int(video_path.stat().st_size / 1024 / 1024) * 3),
        )
        if upload_result.returncode != 0:
            raise RuntimeError(upload_result.stderr.strip() or "Video upload failed")

        flags = " --use-real-results" if job["mode"] == "real" else ""
        inner = (
            "set -o pipefail; "
            f"{shlex.quote(REMOTE_PYTHON)} {shlex.quote(REMOTE_SCRIPT)} "
            f"--video {shlex.quote(remote_video)} "
            f"--duration-minutes {job['duration_minutes']:.4f} "
            f"--output-dir {shlex.quote(remote_output_dir)}{flags} "
            f"2>&1 | tee {shlex.quote(remote_output_dir + '/run.log')}"
        )
        update_job(
            job_id,
            status="running",
            message="A100 实验运行中",
            progress=12,
            started_at=now_iso(),
            started_at_epoch=time.time(),
            remote_dir=remote_job_dir,
        )
        return_code = stream_process(job_id, ssh_base() + ["bash -lc " + shlex.quote(inner)])
        with jobs_lock:
            cancelled = jobs[job_id].get("_cancelled", False)
        if cancelled:
            update_job(job_id, status="cancelled", message="实验已中止", finished_at=now_iso())
            return
        if return_code != 0:
            raise RuntimeError(f"Remote benchmark exited with code {return_code}")

        update_job(job_id, status="downloading", message="正在回传结果", progress=97)
        for filename in ("metrics_dashboard.png", "results.json", "run.log"):
            result = run_capture(
                scp_base()
                + [f"{SSH_HOST}:{remote_output_dir}/{filename}", str(local_dir / filename)],
                timeout=180,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.strip() or f"Failed to download {filename}")

        results = json.loads((local_dir / "results.json").read_text(encoding="utf-8"))
        update_job(
            job_id,
            status="completed",
            message="实验完成",
            progress=100,
            finished_at=now_iso(),
            results=results,
            image_url=f"/api/jobs/{job_id}/files/metrics_dashboard.png",
            results_url=f"/api/jobs/{job_id}/files/results.json",
            log_url=f"/api/jobs/{job_id}/files/run.log",
        )
    except Exception as exc:
        append_log(job_id, f"\nERROR: {exc}\n")
        update_job(job_id, status="failed", message=str(exc), finished_at=now_iso())


@app.get("/")
def index():
    return FileResponse(STATIC_ROOT / "index.html")


@app.get("/api/config")
def config():
    return {
        "ssh_host": SSH_HOST,
        "ssh_port": SSH_PORT,
        "ssh_key": str(SSH_KEY),
        "remote_script": REMOTE_SCRIPT,
        "remote_root": REMOTE_ROOT,
        "max_upload_gb": round(MAX_UPLOAD_BYTES / 1024**3, 1),
    }


@app.post("/api/connection/check")
def check_connection():
    return connection_status()


@app.get("/api/jobs")
def list_jobs():
    with jobs_lock:
        ordered = sorted(jobs.values(), key=lambda item: item["created_at"], reverse=True)
        return [snapshot_job(item) for item in ordered[:10]]


@app.post("/api/jobs")
async def create_job(
    video: UploadFile = File(...),
    duration_minutes: float = Form(8.0),
    mode: str = Form("demo"),
):
    if mode not in {"demo", "real"}:
        raise HTTPException(status_code=400, detail="Invalid benchmark mode")
    if not 0.01 <= duration_minutes <= 240:
        raise HTTPException(status_code=400, detail="Duration must be between 0.01 and 240 minutes")

    suffix = Path(video.filename or "").suffix.lower()
    if suffix not in VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported video format")

    job_id = uuid.uuid4().hex[:12]
    local_dir = RUN_ROOT / job_id
    local_dir.mkdir(parents=True, exist_ok=False)
    local_video = local_dir / f"input{suffix}"
    total = 0
    try:
        with local_video.open("wb") as output:
            while chunk := await video.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_UPLOAD_BYTES:
                    raise HTTPException(status_code=413, detail="Video exceeds upload limit")
                output.write(chunk)
    except Exception:
        local_video.unlink(missing_ok=True)
        raise
    finally:
        await video.close()

    job = {
        "id": job_id,
        "status": "queued",
        "message": "任务已创建",
        "progress": 0,
        "created_at": now_iso(),
        "duration_minutes": duration_minutes,
        "mode": mode,
        "video_name": video.filename,
        "video_size_bytes": total,
        "video_path": str(local_video),
        "local_dir": str(local_dir),
        "log": "",
    }
    with jobs_lock:
        jobs[job_id] = job
    update_job(job_id)
    threading.Thread(target=remote_job, args=(job_id,), daemon=True).start()
    return snapshot_job(job)


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str):
    return snapshot_job(get_job(job_id))


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str):
    job = get_job(job_id)
    with jobs_lock:
        job["_cancelled"] = True
        process = job.get("_process")
    if process and process.poll() is None:
        process.terminate()
    remote_dir = job.get("remote_dir")
    if remote_dir:
        try:
            run_capture(ssh_base() + [f"pkill -f {shlex.quote(remote_dir)} || true"], timeout=15)
        except subprocess.SubprocessError:
            pass
    update_job(job_id, status="cancelled", message="实验已中止", finished_at=now_iso())
    return snapshot_job(job)


@app.post("/api/validation")
def validation():
    health = connection_status()
    if not health.get("connected"):
        raise HTTPException(status_code=503, detail=health.get("message", "A100 unavailable"))
    output_dir = f"{REMOTE_ROOT}/outputs/web_validation"
    command = (
        f"{shlex.quote(REMOTE_PYTHON)} {shlex.quote(REMOTE_SCRIPT)} "
        f"--validate --output-dir {shlex.quote(output_dir)}"
    )
    result = run_capture(ssh_base() + [command], timeout=120)
    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=(result.stdout + result.stderr).strip())
    return {"ok": True, "output": result.stdout.strip()}


@app.get("/api/jobs/{job_id}/files/{filename}")
def job_file(job_id: str, filename: str):
    if filename not in {"metrics_dashboard.png", "results.json", "run.log"}:
        raise HTTPException(status_code=404, detail="File not found")
    path = Path(get_job(job_id)["local_dir"]) / filename
    if not path.is_file():
        raise HTTPException(status_code=404, detail="File not ready")
    media_types = {
        ".png": "image/png",
        ".json": "application/json",
        ".log": "text/plain",
    }
    return FileResponse(path, media_type=media_types[path.suffix], filename=filename)


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("VISPEC_WEB_HOST", "127.0.0.1")
    port = int(os.environ.get("VISPEC_WEB_PORT", "8765"))
    if os.environ.get("VISPEC_NO_BROWSER") != "1":
        threading.Timer(1.2, lambda: webbrowser.open(f"http://{host}:{port}")).start()
    uvicorn.run(app, host=host, port=port, log_level="info")
