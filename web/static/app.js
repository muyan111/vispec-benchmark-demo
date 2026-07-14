const ui = {
  connectionDot: document.querySelector("#connectionDot"),
  connectionText: document.querySelector("#connectionText"),
  refreshConnection: document.querySelector("#refreshConnection"),
  serverAddress: document.querySelector("#serverAddress"),
  videoInput: document.querySelector("#videoInput"),
  dropZone: document.querySelector("#dropZone"),
  dropTitle: document.querySelector("#dropTitle"),
  dropMeta: document.querySelector("#dropMeta"),
  videoPreview: document.querySelector("#videoPreview"),
  videoEmpty: document.querySelector("#videoEmpty"),
  duration: document.querySelector("#duration"),
  startButton: document.querySelector("#startButton"),
  cancelButton: document.querySelector("#cancelButton"),
  validateButton: document.querySelector("#validateButton"),
  jobId: document.querySelector("#jobId"),
  progressBar: document.querySelector("#progressBar"),
  progressValue: document.querySelector("#progressValue"),
  runMessage: document.querySelector("#runMessage"),
  logOutput: document.querySelector("#logOutput"),
  resultEmpty: document.querySelector("#resultEmpty"),
  resultContent: document.querySelector("#resultContent"),
  resultTimestamp: document.querySelector("#resultTimestamp"),
  resultImage: document.querySelector("#resultImage"),
  metricsBody: document.querySelector("#metricsBody"),
  videoFacts: document.querySelector("#videoFacts"),
  connectionFacts: document.querySelector("#connectionFacts"),
  downloadImage: document.querySelector("#downloadImage"),
  downloadJson: document.querySelector("#downloadJson"),
  downloadLog: document.querySelector("#downloadLog"),
  toast: document.querySelector("#toast"),
};

let selectedFile = null;
let currentJobId = null;
let pollTimer = null;
let connectionReady = false;
let previewUrl = null;

function showToast(message, timeout = 4200) {
  ui.toast.textContent = message;
  ui.toast.hidden = false;
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => { ui.toast.hidden = true; }, timeout);
}

function formatBytes(bytes) {
  if (!Number.isFinite(bytes)) return "-";
  const units = ["B", "KB", "MB", "GB"];
  let value = bytes;
  let index = 0;
  while (value >= 1024 && index < units.length - 1) {
    value /= 1024;
    index += 1;
  }
  return `${value.toFixed(index > 1 ? 2 : 0)} ${units[index]}`;
}

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>'"]/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    "'": "&#39;",
    '"': "&quot;",
  })[character]);
}

function setConnection(connected, text) {
  connectionReady = connected;
  ui.connectionDot.className = `status-dot ${connected ? "connected" : "disconnected"}`;
  ui.connectionText.textContent = text;
  ui.startButton.disabled = !(connected && selectedFile) || Boolean(currentJobId);
}

async function fetchJson(url, options = {}) {
  const response = await fetch(url, options);
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload.detail || `Request failed: ${response.status}`);
  return payload;
}

async function loadConfig() {
  const config = await fetchJson("/api/config");
  ui.serverAddress.textContent = `${config.ssh_host}:${config.ssh_port}`;
  ui.connectionFacts.innerHTML = Object.entries({
    "SSH 入口": `${config.ssh_host}:${config.ssh_port}`,
    "本机密钥": config.ssh_key,
    "服务器脚本": config.remote_script,
    "服务器目录": config.remote_root,
    "上传上限": `${config.max_upload_gb} GB`,
  }).map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
}

async function checkConnection(showResult = false) {
  ui.connectionDot.className = "status-dot pending";
  ui.connectionText.textContent = "正在检查连接";
  ui.refreshConnection.disabled = true;
  try {
    const health = await fetchJson("/api/connection/check", { method: "POST" });
    const ok = Boolean(health.connected && health.script_ready);
    setConnection(ok, ok ? "A100 已连接" : "隧道或脚本未就绪");
    if (showResult) showToast(ok ? "A100 连接正常" : health.message);
  } catch (error) {
    setConnection(false, "A100 未连接");
    if (showResult) showToast(error.message);
  } finally {
    ui.refreshConnection.disabled = false;
  }
}

function selectFile(file) {
  const extension = file ? file.name.toLowerCase().split(".").pop() : "";
  const allowedExtensions = ["mp4", "mov", "mkv", "webm", "avi", "m4v"];
  if (!file || (!file.type.startsWith("video/") && !allowedExtensions.includes(extension))) {
    showToast("请选择视频文件");
    return;
  }
  selectedFile = file;
  ui.dropTitle.textContent = file.name;
  ui.dropMeta.textContent = formatBytes(file.size);
  if (previewUrl) URL.revokeObjectURL(previewUrl);
  previewUrl = URL.createObjectURL(file);
  ui.videoPreview.src = previewUrl;
  ui.videoPreview.hidden = false;
  ui.videoEmpty.hidden = true;
  ui.startButton.disabled = !connectionReady || Boolean(currentJobId);
}

function setProgress(value, message) {
  const safeValue = Math.max(0, Math.min(100, Number(value) || 0));
  ui.progressBar.style.width = `${safeValue}%`;
  ui.progressValue.textContent = `${safeValue}%`;
  if (message) ui.runMessage.textContent = message;
}

function uploadJob(formData) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", "/api/jobs");
    xhr.responseType = "json";
    xhr.upload.addEventListener("progress", (event) => {
      if (event.lengthComputable) {
        const progress = Math.round(event.loaded / event.total * 7);
        setProgress(progress, `正在提交视频 ${Math.round(event.loaded / event.total * 100)}%`);
      }
    });
    xhr.addEventListener("load", () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve(xhr.response);
      else reject(new Error(xhr.response?.detail || `Upload failed: ${xhr.status}`));
    });
    xhr.addEventListener("error", () => reject(new Error("视频提交失败")));
    xhr.send(formData);
  });
}

async function startJob() {
  if (!selectedFile || !connectionReady) return;
  const duration = Number(ui.duration.value);
  if (!Number.isFinite(duration) || duration < 0.01 || duration > 240) {
    showToast("运行时长需为 0.01 到 240 分钟");
    return;
  }

  const form = new FormData();
  form.append("video", selectedFile);
  form.append("duration_minutes", String(duration));
  form.append("mode", document.querySelector('input[name="mode"]:checked').value);

  ui.startButton.disabled = true;
  ui.resultContent.hidden = true;
  ui.resultEmpty.hidden = false;
  ui.logOutput.textContent = "正在提交视频...";
  setProgress(1, "正在提交任务");
  try {
    const job = await uploadJob(form);
    currentJobId = job.id;
    ui.jobId.textContent = `任务 ${job.id}`;
    ui.cancelButton.disabled = false;
    pollJob();
  } catch (error) {
    currentJobId = null;
    ui.startButton.disabled = !(connectionReady && selectedFile);
    setProgress(0, "启动失败");
    ui.logOutput.textContent += `\nERROR: ${error.message}`;
    showToast(error.message);
  }
}

function renderResults(job) {
  const result = job.results || {};
  const rows = result.metrics || [];
  ui.metricsBody.innerHTML = rows.map((row) => `
    <tr>
      <td>${escapeHtml(row.task)}</td>
      <td>${Number(row.baseline_tokens_per_s).toFixed(2)}</td>
      <td>${Number(row.medusa_tokens_per_s).toFixed(2)}</td>
      <td>${Number(row.ours_tokens_per_s).toFixed(2)}</td>
      <td>${Number(row.ours_vs_baseline_speedup).toFixed(2)}x</td>
    </tr>
  `).join("");
  const video = result.input_video || {};
  ui.videoFacts.innerHTML = [
    ["输入视频", video.filename || job.video_name],
    ["文件大小", formatBytes(video.size_bytes || job.video_size_bytes)],
    ["SHA-256", video.sha256 || "-"],
    ["模式", job.mode === "real" ? "历史实测" : "演示数据"],
  ].map(([key, value]) => `<dt>${escapeHtml(key)}</dt><dd>${escapeHtml(value)}</dd>`).join("");
  const cacheKey = Date.now();
  ui.resultImage.src = `${job.image_url}?v=${cacheKey}`;
  ui.downloadImage.href = job.image_url;
  ui.downloadJson.href = job.results_url;
  ui.downloadLog.href = job.log_url;
  ui.resultTimestamp.textContent = job.finished_at || "实验完成";
  ui.resultEmpty.hidden = true;
  ui.resultContent.hidden = false;
}

async function pollJob() {
  if (!currentJobId) return;
  try {
    const job = await fetchJson(`/api/jobs/${currentJobId}`);
    setProgress(job.progress, job.message);
    ui.logOutput.textContent = job.log || "任务已创建，等待服务器输出...";
    ui.logOutput.scrollTop = ui.logOutput.scrollHeight;
    if (job.status === "completed") {
      renderResults(job);
      finishPolling("实验完成");
      return;
    }
    if (["failed", "cancelled"].includes(job.status)) {
      finishPolling(job.message);
      return;
    }
    pollTimer = window.setTimeout(pollJob, 1000);
  } catch (error) {
    ui.runMessage.textContent = "状态读取失败，正在重试";
    pollTimer = window.setTimeout(pollJob, 2500);
  }
}

function finishPolling(message) {
  window.clearTimeout(pollTimer);
  pollTimer = null;
  currentJobId = null;
  ui.cancelButton.disabled = true;
  ui.startButton.disabled = !(connectionReady && selectedFile);
  showToast(message);
}

async function cancelJob() {
  if (!currentJobId) return;
  ui.cancelButton.disabled = true;
  try {
    const job = await fetchJson(`/api/jobs/${currentJobId}/cancel`, { method: "POST" });
    setProgress(job.progress, job.message);
    finishPolling(job.message);
  } catch (error) {
    showToast(error.message);
    ui.cancelButton.disabled = false;
  }
}

async function validateHistory() {
  ui.validateButton.disabled = true;
  try {
    const payload = await fetchJson("/api/validation", { method: "POST" });
    ui.logOutput.textContent = payload.output;
    showToast("历史结果验证完成");
  } catch (error) {
    showToast(error.message, 7000);
  } finally {
    ui.validateButton.disabled = false;
  }
}

ui.videoInput.addEventListener("change", () => selectFile(ui.videoInput.files[0]));
ui.dropZone.addEventListener("dragover", (event) => { event.preventDefault(); ui.dropZone.classList.add("dragging"); });
ui.dropZone.addEventListener("dragleave", () => ui.dropZone.classList.remove("dragging"));
ui.dropZone.addEventListener("drop", (event) => {
  event.preventDefault();
  ui.dropZone.classList.remove("dragging");
  selectFile(event.dataTransfer.files[0]);
});
ui.refreshConnection.addEventListener("click", () => checkConnection(true));
ui.startButton.addEventListener("click", startJob);
ui.cancelButton.addEventListener("click", cancelJob);
ui.validateButton.addEventListener("click", validateHistory);

Promise.all([loadConfig(), checkConnection()]).catch((error) => showToast(error.message));
window.setInterval(() => { if (!currentJobId) checkConnection(); }, 15000);
