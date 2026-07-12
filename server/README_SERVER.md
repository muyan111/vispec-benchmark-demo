# Server Runbook

This guide starts after you have logged into the A100 node.

## 1. Enter the Container

```bash
sudo -iu work
docker start luboyan1
docker exec -it luboyan1 /bin/bash
```

Expected prompt:

```text
(base) root@bj9-llm-g8a100-node00:/#
```

## 2. Clone This Repository

```bash
cd /home
git clone <YOUR_GITHUB_REPO_URL> vispec-benchmark-demo
cd /home/vispec-benchmark-demo
```

## 3. Prepare Environment

```bash
bash server/setup_server.sh
```

If Chinese text in PNG appears as boxes, upload a Chinese font to:

```text
/home/vispec_repro/fonts/simhei.ttf
```

## 4. Run the Benchmark-Style Demo

Default 8-minute run:

```bash
/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py \
  | tee /home/vispec_repro/outputs/benchmark_dashboard/run.log
```

Quick smoke test:

```bash
/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py \
  --duration-minutes 0.05 \
  --output-dir /home/vispec_repro/outputs/benchmark_dashboard_smoke
```

## 5. Inspect Server Results

```bash
ls -lh /home/vispec_repro/outputs/benchmark_dashboard/
cat /home/vispec_repro/outputs/benchmark_dashboard/results.json
tail -80 /home/vispec_repro/outputs/benchmark_dashboard/run.log
```

## 6. Manual Validation

```bash
/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py --validate
```

```bash
/root/miniconda3/envs/rekv/bin/python server/run_benchmark.py \
  --use-real-results \
  --output-dir /home/vispec_repro/outputs/benchmark_dashboard_real
```
