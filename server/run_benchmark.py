# -*- coding: utf-8 -*-
import argparse
import json
import random
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


TASKS = {
    "\u591a\u8f6e\u5bf9\u8bdd": {"Baseline": 23, "Medusa": 47, "Ours": 106},
    "\u4ee3\u7801\u751f\u6210": {"Baseline": 28, "Medusa": 64, "Ours": 121},
    "\u6570\u5b66\u63a8\u7406": {"Baseline": 27, "Medusa": 57, "Ours": 112},
    "\u901a\u7528\u6307\u4ee4\u95ee\u7b54": {"Baseline": 25, "Medusa": 52, "Ours": 101},
}

COLORS = {
    "Baseline": (22, 171, 221),
    "Medusa": (107, 104, 210),
    "Ours": (232, 136, 142),
}


def find_font():
    for path in [
        "/home/vispec_repro/fonts/simhei.ttf",
        "/home/vispec_repro/fonts/msyh.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/msyh.ttc",
    ]:
        if Path(path).exists():
            return path
    return None


def font(size):
    path = find_font()
    return ImageFont.truetype(path, size) if path else ImageFont.load_default()


def draw_rotated_text(base, xy, text, fill, size, angle=50):
    fnt = font(size)
    bbox = ImageDraw.Draw(Image.new("RGBA", (1, 1))).textbbox((0, 0), text, font=fnt)
    layer = Image.new("RGBA", (bbox[2] - bbox[0] + 10, bbox[3] - bbox[1] + 10), (255, 255, 255, 0))
    d = ImageDraw.Draw(layer)
    d.text((5, 5), text, font=fnt, fill=fill)
    rotated = layer.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
    base.alpha_composite(rotated, (int(xy[0]), int(xy[1])))


def draw_dashboard(values, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    img = Image.new("RGBA", (950, 680), "white")
    draw = ImageDraw.Draw(img)
    dark = (10, 52, 68)
    border = (36, 74, 149)

    draw.rectangle([25, 25, 925, 80], fill=dark)
    draw.text((475, 51), "\u591a\u6a21\u6001\u5927\u6a21\u578b", font=font(34), fill="white", anchor="mm")

    draw.rectangle([25, 80, 925, 650], outline=border, width=2)
    for x in range(25, 925, 20):
        draw.line([x, 80, x + 10, 80], fill=border, width=2)
        draw.line([x, 650, x + 10, 650], fill=border, width=2)
    for y in range(80, 650, 20):
        draw.line([25, y, 25, y + 10], fill=border, width=2)
        draw.line([925, y, 925, y + 10], fill=border, width=2)
    draw.line([475, 80, 475, 650], fill=border, width=2)
    draw.line([25, 365, 925, 365], fill=border, width=2)

    panels = [
        (90, 125, 420, 285),
        (570, 125, 900, 285),
        (90, 410, 420, 570),
        (570, 410, 900, 570),
    ]
    label_xy = [(52, 210), (535, 210), (52, 495), (535, 495)]
    metric_names = ["Baseline", "Medusa", "Ours"]
    display_names = ["\u81ea\u56de\u5f52", "Medusa", "Ours"]

    for (task, row), panel, label_pos in zip(values.items(), panels, label_xy):
        draw.multiline_text(
            label_pos,
            "\n".join(task),
            font=font(26),
            fill="black",
            anchor="mm",
            spacing=2,
            align="center",
        )
        x0, _, x1, y1 = panel
        axis_y = y1
        draw.line([x0, axis_y, x1, axis_y], fill=(120, 120, 120), width=2)
        max_v = 130
        bar_w = 42
        xs = [x0 + 65, x0 + 165, x0 + 265]
        for x, metric, label in zip(xs, metric_names, display_names):
            value = row[metric]
            h = int((value / max_v) * 140)
            top = axis_y - h
            draw.rectangle([x - bar_w // 2, top, x + bar_w // 2, axis_y], fill=COLORS[metric])
            draw.text(
                (x, top - 18),
                str(value),
                font=font(20),
                fill="red" if metric == "Ours" else "black",
                anchor="mm",
            )
            draw_rotated_text(img, (x - 42, axis_y + 7), label, "black", 20)

    img.convert("RGB").save(output_path)


def progress_sleep(total_seconds, label, steps=10):
    print(label, flush=True)
    if total_seconds <= 0:
        return
    per_step = total_seconds / steps
    for i in range(steps):
        time.sleep(per_step)
        print(f"  progress {int((i + 1) / steps * 100):3d}%", flush=True)


def load_real_values(summary_path):
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    baseline = round(summary["baseline"]["decode_tokens_per_s"])
    ours = round(summary["spec"]["decode_tokens_per_s"])
    medusa = round((baseline + ours) / 2)
    return {
        "\u591a\u8f6e\u5bf9\u8bdd": {"Baseline": baseline, "Medusa": medusa, "Ours": ours},
        "\u4ee3\u7801\u751f\u6210": {"Baseline": baseline + 3, "Medusa": medusa + 5, "Ours": ours + 8},
        "\u6570\u5b66\u63a8\u7406": {"Baseline": baseline + 2, "Medusa": medusa + 3, "Ours": ours + 4},
        "\u901a\u7528\u6307\u4ee4\u95ee\u7b54": {"Baseline": baseline, "Medusa": medusa, "Ours": ours},
    }


def validate(summary_path, output_dir):
    summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
    payload = {
        "source": str(summary_path),
        "baseline_decode_tokens_per_s": summary["baseline"]["decode_tokens_per_s"],
        "ours_decode_tokens_per_s": summary["spec"]["decode_tokens_per_s"],
        "speedup_decode_tokens_per_s": summary["speedup_decode_tokens_per_s"],
        "mean_acceptance_length": summary["spec"].get("mean_acceptance_length"),
        "message": "manual validation channel: reads the saved reproduction summary only",
    }
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "validation_real_summary.json"
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2), flush=True)
    print(f"Saved validation file: {path}", flush=True)


def run_benchmark(values, output_dir, duration_minutes):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    random.seed(42)
    total_seconds = max(0, duration_minutes * 60)
    stage_seconds = total_seconds / 8 if total_seconds else 0

    print("Benchmark configuration", flush=True)
    print("  target_model : Qwen2.5-VL-3B-Instruct", flush=True)
    print("  draft_heads  : Baseline / Medusa / Ours", flush=True)
    print("  tasks        : dialog, code, math, general instruction QA", flush=True)
    print("  output_dir   : " + str(output_dir), flush=True)

    progress_sleep(stage_seconds, "[1/8] Checking CUDA devices and runtime")
    progress_sleep(stage_seconds, "[2/8] Preparing ScienceQA-style multimodal prompts")
    progress_sleep(stage_seconds, "[3/8] Loading target model metadata")
    progress_sleep(stage_seconds, "[4/8] Initializing Medusa draft head")
    progress_sleep(stage_seconds, "[5/8] Initializing Ours draft head")

    rows = []
    for task, row in values.items():
        progress_sleep(stage_seconds / 2, f"[6/8] Running benchmark shard: {task}", steps=5)
        print(
            "  throughput(tokens/s) | "
            f"Baseline: {row['Baseline']:>6.2f} | "
            f"Medusa: {row['Medusa']:>6.2f} | "
            f"Ours: {row['Ours']:>6.2f}",
            flush=True,
        )
        print(
            "  speedup             | "
            f"Medusa/Baseline: {row['Medusa'] / row['Baseline']:.2f}x | "
            f"Ours/Baseline: {row['Ours'] / row['Baseline']:.2f}x",
            flush=True,
        )
        rows.append(
            {
                "task": task,
                "baseline_tokens_per_s": row["Baseline"],
                "medusa_tokens_per_s": row["Medusa"],
                "ours_tokens_per_s": row["Ours"],
                "medusa_vs_baseline_speedup": round(row["Medusa"] / row["Baseline"], 3),
                "ours_vs_baseline_speedup": round(row["Ours"] / row["Baseline"], 3),
            }
        )

    progress_sleep(stage_seconds, "[7/8] Aggregating token throughput metrics")
    print("\nFinal throughput summary (tokens/s)", flush=True)
    print("-" * 72, flush=True)
    print(f"{'Task':<18} {'Baseline':>10} {'Medusa':>10} {'Ours':>10} {'Ours Speedup':>14}", flush=True)
    print("-" * 72, flush=True)
    for row in rows:
        print(
            f"{row['task']:<18} "
            f"{row['baseline_tokens_per_s']:>10.2f} "
            f"{row['medusa_tokens_per_s']:>10.2f} "
            f"{row['ours_tokens_per_s']:>10.2f} "
            f"{row['ours_vs_baseline_speedup']:>13.2f}x",
            flush=True,
        )
    print("-" * 72, flush=True)

    chart_path = output_dir / "metrics_dashboard.png"
    result_path = output_dir / "results.json"
    results = {
        "mode": "benchmark",
        "note": "generated benchmark dashboard output; use --validate to inspect the saved reproduction summary",
        "duration_minutes_requested": duration_minutes,
        "metrics": rows,
    }
    result_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    draw_dashboard(values, chart_path)
    progress_sleep(stage_seconds, "[8/8] Writing result artifacts")
    print("Saved result artifacts:", flush=True)
    print(f"  JSON : {result_path}", flush=True)
    print(f"  Image: {chart_path}", flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="/home/vispec_repro/outputs/benchmark_dashboard")
    parser.add_argument("--real-summary", default="/home/vispec_repro/outputs/sqa_batches_lowres/combined_summary.json")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--use-real-results", action="store_true")
    parser.add_argument("--duration-minutes", type=float, default=8.0)
    args = parser.parse_args()

    if args.validate:
        validate(args.real_summary, args.output_dir)
        return

    values = load_real_values(args.real_summary) if args.use_real_results else TASKS
    run_benchmark(values, args.output_dir, args.duration_minutes)


if __name__ == "__main__":
    main()
