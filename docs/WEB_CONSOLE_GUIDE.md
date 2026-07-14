# ViSpec Web Console: 从连接 A100 到网页出图

这套控制台把原来的多步操作合并成一个本地网页。浏览器只负责选择视频和展示状态；Windows 本地服务负责通过 SSH 反向隧道把视频送到 A100；A100 完成运行后，本地服务自动拉回 PNG、JSON 和日志，并显示在网页中。

```text
浏览器 http://127.0.0.1:8765
        |
        v
Windows 本地 Python 服务
        |
        | SSH/SCP: root@localhost:2225
        v
Windows 反向隧道入口 2225
        |
        v
A100 容器 sshd 127.0.0.1:2224
        |
        v
/home/vispec_repro/run_benchmark.py
```

## 一、只需准备一次

### 1. Windows 软件

- Python 3.10 或更高版本。
- Windows OpenSSH Client。
- Windows OpenSSH Server，用于接收 A100 主动建立的反向隧道。
- CorpLink/小米 VPN。
- 本仓库代码。

管理员 PowerShell 中检查 OpenSSH Server：

```powershell
Get-Service sshd
```

如果服务尚未安装：

```powershell
Add-WindowsCapability -Online -Name OpenSSH.Server~~~~0.0.1.0
Start-Service sshd
Set-Service -Name sshd -StartupType Automatic
```

本地控制 A100 使用的私钥默认位置：

```text
C:\Users\DELL\.ssh\vispec_codex
```

网页服务不会读取或展示密钥内容，仓库也不会上传任何 SSH 密钥。

### 2. A100 容器

服务器需要具备：

```text
/root/miniconda3/envs/rekv/bin/python
/home/vispec_repro/run_benchmark.py
/root/.ssh/vispec_tunnel_ed25519
127.0.0.1:2224 上运行的容器 sshd
```

首次拉取和安装：

```bash
cd /home
git clone https://github.com/muyan111/vispec-benchmark-demo.git
cd /home/vispec-benchmark-demo
bash server/setup_server.sh
```

如果仓库已经存在：

```bash
cd /home/vispec-benchmark-demo
git pull
bash server/setup_server.sh
```

`setup_server.sh` 会安装服务器端最小依赖，并把最新运行脚本复制到：

```text
/home/vispec_repro/run_benchmark.py
```

## 二、每次开机或断线后的连接步骤

### 1. Windows 连接 CorpLink

在 CMD 中执行：

```cmd
ipconfig
```

记录 `CorpLink TAP-Windows6` 下的 IPv4 地址，例如：

```text
10.56.240.56
```

该地址每次重新连接 VPN 后可能变化。

### 2. 登录 A100 并进入容器

```cmd
ssh -tt -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -p 22 p-gongqinan@relay.xiaomi.com
```

在 Relay 中选择：

```text
bj9-llm-g8a100-node00.alicn.idc.xiaomi.com
```

进入节点后：

```bash
sudo -iu work
docker start luboyan1
docker exec -it luboyan1 /bin/bash
```

预期提示符：

```text
(base) root@bj9-llm-g8a100-node00:/#
```

### 3. 恢复容器 sshd

```bash
mkdir -p /run/sshd /root/.ssh

if ! pgrep -af '/usr/sbin/sshd -D -f /root/.ssh/vispec_sshd_config' >/dev/null; then
  nohup /usr/sbin/sshd -D \
    -f /root/.ssh/vispec_sshd_config \
    -E /root/.ssh/vispec_sshd.log >/dev/null 2>&1 &
fi

tail -20 /root/.ssh/vispec_sshd.log
```

正常日志应包含：

```text
Server listening on 127.0.0.1 port 2224.
```

### 4. 建立反向隧道

在 A100 容器中的仓库目录执行，把示例 IP 换成当前 CorpLink IPv4：

```bash
cd /home/vispec-benchmark-demo
bash server/start_reverse_tunnel.sh 10.56.240.56
```

正常情况下日志没有 `Permission denied`、`Connection refused` 或 `remote port forwarding failed`。

这条命令使用 `nohup`，因此 Relay 登录窗口随后断开通常不会结束隧道。Windows 必须继续保持开机、CorpLink 在线且 `sshd` 服务运行。

### 5. Windows 验证隧道

新开普通 PowerShell：

```powershell
ssh -i $env:USERPROFILE\.ssh\vispec_codex `
  -p 2225 `
  -o ConnectTimeout=8 `
  -o StrictHostKeyChecking=no `
  -o UserKnownHostsFile=$env:USERPROFILE\.ssh\vispec_node00_known_hosts `
  root@localhost "whoami && hostname && test -f /home/vispec_repro/run_benchmark.py && echo SCRIPT_READY"
```

预期至少看到：

```text
root
bj9-llm-g8a100-node00.alicn.idc.xiaomi.com
SCRIPT_READY
```

## 三、一键打开网页

在仓库根目录双击：

```text
start_console.cmd
```

首次运行会自动创建 `.venv` 并安装本地网页依赖。随后浏览器自动打开：

```text
http://127.0.0.1:8765
```

也可以在 PowerShell 中启动：

```powershell
cd C:\Users\DELL\Documents\vispec-benchmark-demo
powershell -ExecutionPolicy Bypass -File .\local\start_console.ps1
```

启动网页的 CMD/PowerShell 窗口需要保持打开。

## 四、网页操作

1. 顶部连接状态显示 `A100 已连接`。
2. 选择或拖入视频，页面会先在本地预览。
3. 设置运行时长。正式演示默认 8 分钟；联调可填 `0.05`。
4. 选择 `演示数据` 或 `历史实测`。
5. 点击 `开始实验`。
6. 页面依次完成本机接收视频、上传 A100、运行脚本、拉回结果。
7. 完成后直接展示结果图和 Baseline/Medusa/Ours tokens/s 表格。

网页还提供：

- 实时服务器控制台输出。
- 中止当前任务。
- 手动验证历史结果。
- 下载结果图、JSON 和日志。

## 五、结果保存位置

Windows 本机：

```text
web_runs/<任务ID>/
  input.mp4
  metrics_dashboard.png
  results.json
  run.log
  state.json
```

A100 容器：

```text
/home/vispec_repro/web_jobs/<任务ID>/
  input.mp4
  output/metrics_dashboard.png
  output/results.json
  output/run.log
```

## 六、常见故障

### 网页显示 A100 未连接

依次检查：

```powershell
Get-Service sshd
Test-NetConnection 127.0.0.1 -Port 2225
```

如果 2225 不通，通常是 Windows CorpLink IP 已变化或服务器反向隧道进程已退出。重新读取 CorpLink IPv4，并在 A100 容器重跑 `start_reverse_tunnel.sh`。

### 网页显示服务器脚本不存在

```bash
cd /home/vispec-benchmark-demo
git pull
bash server/setup_server.sh
```

### 视频上传后任务失败

页面日志会保留 SSH、SCP 和服务器脚本的错误。也可在 A100 查看：

```bash
find /home/vispec_repro/web_jobs -maxdepth 3 -name run.log -type f -print
```

### 电脑睡眠导致中断

演示期间保持 Windows 不睡眠，并保持 CorpLink 连接。管理员 CMD 可临时执行：

```cmd
powercfg /change standby-timeout-ac 0
```

实验结束后可恢复，例如：

```cmd
powercfg /change standby-timeout-ac 30
```

## 七、可调整配置

本地后端支持环境变量覆盖默认值：

```text
VISPEC_SSH_PORT
VISPEC_SSH_HOST
VISPEC_SSH_KEY
VISPEC_KNOWN_HOSTS
VISPEC_REMOTE_ROOT
VISPEC_REMOTE_PYTHON
VISPEC_REMOTE_SCRIPT
VISPEC_WEB_PORT
VISPEC_MAX_UPLOAD_BYTES
```

默认网页仅监听 `127.0.0.1`，局域网其他机器无法访问；SSH 密钥、视频和实验结果不会提交到 GitHub。
