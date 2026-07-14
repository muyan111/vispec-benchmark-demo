# ViSpec Benchmark Demo

This repository contains a self-contained benchmark-style demo for the A100 server workflow.

It is designed for presentation and operation rehearsal:

- Runs from a fresh server terminal after entering the A100 container.
- Prints `Baseline / Medusa / Ours` throughput in tokens/s.
- Generates a JSON result file and a PNG dashboard.
- Keeps manual validation hooks for reading the previous real reproduction summary.
- Includes a local web console that uploads a video, starts the A100 run, streams logs, and displays returned results.

## Web Console

The quickest Windows workflow is:

```text
1. Keep CorpLink and the A100 reverse tunnel connected.
2. Double-click start_console.cmd.
3. Select a video and click Start.
```

The browser opens at:

```text
http://127.0.0.1:8765
```

Full connection and recovery instructions are in [docs/WEB_CONSOLE_GUIDE.md](docs/WEB_CONSOLE_GUIDE.md).

Large model weights, datasets, SSH keys, and private credentials are intentionally not included.

## Repository Layout

```text
server/run_benchmark.py          Main benchmark-style runner.
server/setup_server.sh           Installs minimal Python dependencies and prepares folders.
server/start_reverse_tunnel.sh   Restarts the A100-to-Windows reverse SSH tunnel.
server/README_SERVER.md          Server-side runbook.
local/pull_results.ps1           Pulls generated PNG/JSON/log back to Windows through the SSH tunnel.
local/install_console.ps1        Creates the local web environment.
local/start_console.ps1          Starts the local browser console.
start_console.cmd                Double-click launcher for Windows.
web/                             Local API and HTML/CSS/JS console.
docs/                            Operation manuals and notes.
examples/                        Example generated outputs.
requirements.txt                 Minimal Python package requirements.
requirements-server.txt          A100-only Python dependency.
requirements-web.txt             Windows web-console dependencies.
.gitignore                       Excludes models, data, logs, credentials, and generated caches.
```

## Quick Start on A100 Server

After logging into the A100 node and entering the container:

```bash
cd /home
git clone <YOUR_GITHUB_REPO_URL> vispec-benchmark-demo
cd /home/vispec-benchmark-demo
bash server/setup_server.sh

/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py \
  | tee /home/vispec_repro/outputs/benchmark_dashboard/run.log
```

The default run lasts about 8 minutes.

For a quick smoke test:

```bash
/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py \
  --duration-minutes 0.05 \
  --output-dir /home/vispec_repro/outputs/benchmark_dashboard_smoke
```

## Expected Console Output

The console prints throughput for each task:

```text
throughput(tokens/s) | Baseline:  23.00 | Medusa:  47.00 | Ours: 106.00
speedup             | Medusa/Baseline: 2.04x | Ours/Baseline: 4.61x
```

Final summary:

```text
Final throughput summary (tokens/s)
------------------------------------------------------------------------
Task                 Baseline     Medusa       Ours   Ours Speedup
------------------------------------------------------------------------
多轮对话                    23.00      47.00     106.00          4.61x
代码生成                    28.00      64.00     121.00          4.32x
数学推理                    27.00      57.00     112.00          4.15x
通用指令问答                  25.00      52.00     101.00          4.04x
------------------------------------------------------------------------
```

## Output Files

Default output directory:

```text
/home/vispec_repro/outputs/benchmark_dashboard/
```

Generated artifacts:

```text
results.json
metrics_dashboard.png
run.log
```

The server terminal usually cannot preview PNG images directly. Use `local/pull_results.ps1` from Windows to copy them back.

## Manual Validation Hooks

Read the previous real reproduction summary:

```bash
/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py --validate
```

Use the previous real summary to render an alternate chart:

```bash
/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py \
  --use-real-results \
  --output-dir /home/vispec_repro/outputs/benchmark_dashboard_real
```

The default benchmark dashboard remains presentation-oriented and does not require loading the full model.
