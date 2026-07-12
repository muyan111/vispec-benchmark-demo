# Environment and Assets

This demo is intentionally lightweight. It does not require downloading model weights to run the presentation benchmark dashboard.

## Required on the Server

- Linux shell inside the A100 container.
- Python 3.10+.
- `Pillow` Python package.
- Optional Chinese font for PNG rendering:
  - `/home/vispec_repro/fonts/simhei.ttf`
  - or `/home/vispec_repro/fonts/msyh.ttc`

The known working Python path on the Xiaomi A100 container is:

```bash
/root/miniconda3/envs/rekv/bin/python
```

## Install Minimal Environment

After cloning the repository on the server:

```bash
bash server/setup_server.sh
```

This installs:

```text
Pillow>=10.0.0
```

## Optional Real Validation Assets

The `--validate` and `--use-real-results` modes expect a previous reproduction summary at:

```text
/home/vispec_repro/outputs/sqa_batches_lowres/combined_summary.json
```

If that file is not present, the default benchmark mode still works.

## Not Included

The following are intentionally excluded from Git:

- Qwen / ViSpec model weights.
- ScienceQA dataset files.
- SSH private keys.
- Relay login records.
- Generated cache files and logs.

These exclusions keep the repository lightweight and safe to publish.
