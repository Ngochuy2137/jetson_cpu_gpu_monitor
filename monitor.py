#!/usr/bin/env python3
"""
Log CPU and GPU usage to an Excel file on Jetson (or any Linux host with psutil).

CPU sampling follows main_controller/observer.py:
  psutil.cpu_percent(interval=0, percpu=True)

GPU load is read from Jetson sysfs (value / 10 = percent).
"""
from __future__ import annotations

import argparse
import statistics
import sys
import time
from datetime import datetime
from pathlib import Path

try:
    import psutil
except ImportError:
    print("Install dependencies: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)

try:
    from openpyxl import Workbook
except ImportError:
    print("Install dependencies: pip install -r requirements.txt", file=sys.stderr)
    raise SystemExit(1)

DEFAULT_GPU_LOAD_PATHS = (
    "/sys/devices/platform/bus@0/17000000.gpu/load",
    "/sys/class/devfreq/17000000.gpu/device/load",
)


def find_gpu_load_path() -> Path | None:
    for path_str in DEFAULT_GPU_LOAD_PATHS:
        path = Path(path_str)
        if path.is_file():
            return path

    devfreq = Path("/sys/class/devfreq")
    if devfreq.is_dir():
        for entry in devfreq.iterdir():
            name_file = entry / "device/of_node/name"
            if name_file.is_file():
                name = name_file.read_text(encoding="utf-8", errors="ignore").strip("\x00")
                if name == "gpu":
                    load_file = entry / "device/load"
                    if load_file.is_file():
                        return load_file
    return None


def read_gpu_percent(gpu_load_path: Path | None) -> float | None:
    if gpu_load_path is None:
        return None
    try:
        raw = gpu_load_path.read_text(encoding="utf-8").strip()
        return float(raw) / 10.0
    except (OSError, ValueError):
        return None


def get_cpu_per_core() -> list[float]:
    return list(psutil.cpu_percent(interval=0, percpu=True))


def count_cores_above(per_core: list[float], threshold: float) -> int:
    return sum(1 for value in per_core if value > threshold)


def default_output_path() -> Path:
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return Path(__file__).resolve().parent / f"cpu_gpu_monitor_{stamp}.xlsx"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Monitor CPU/GPU usage and save samples to an Excel file."
    )
    parser.add_argument(
        "--hz",
        type=float,
        default=10.0,
        help="Sampling rate in Hz (default: 10)",
    )
    parser.add_argument(
        "-x",
        "--threshold",
        type=float,
        default=80.0,
        help="CPU core usage threshold in percent for the core-count column (default: 80)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="Run duration in seconds (0 = until Ctrl+C, default: 0)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output .xlsx path (default: cpu_gpu_monitor_<timestamp>.xlsx in package dir)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.hz <= 0:
        print("--hz must be > 0", file=sys.stderr)
        return 1
    if not 0 <= args.threshold <= 100:
        print("--threshold must be between 0 and 100", file=sys.stderr)
        return 1

    interval = 1.0 / args.hz
    output_path = args.output or default_output_path()
    gpu_load_path = find_gpu_load_path()
    cores_col = f"cores_above_{args.threshold:g}pct"

    if gpu_load_path is None:
        print("Warning: GPU load sysfs not found; GPU column will be empty.", file=sys.stderr)
    else:
        print(f"GPU load path: {gpu_load_path}")

    # Prime psutil counters (same pattern as main_controller resource monitor).
    psutil.cpu_percent(interval=0, percpu=True)

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "monitor"
    sheet.append(["timestamp", "cpu_avg_pct", "gpu_pct", cores_col])

    rows: list[tuple[str, float, float | None, int]] = []
    start = time.monotonic()
    next_sample = start
    sample_count = 0

    print(
        f"Sampling at {args.hz:g} Hz, threshold={args.threshold:g}%%, "
        f"output={output_path}"
    )

    try:
        while True:
            now = time.monotonic()
            if args.duration > 0 and (now - start) >= args.duration:
                break

            if now < next_sample:
                time.sleep(min(0.001, next_sample - now))
                continue

            per_core = get_cpu_per_core()
            cpu_avg = statistics.fmean(per_core) if per_core else 0.0
            gpu_pct = read_gpu_percent(gpu_load_path)
            cores_above = count_cores_above(per_core, args.threshold)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            rows.append((timestamp, cpu_avg, gpu_pct, cores_above))
            sample_count += 1
            next_sample += interval

            if sample_count % int(max(args.hz, 1)) == 0:
                gpu_text = "n/a" if gpu_pct is None else f"{gpu_pct:.1f}"
                print(
                    f"[{timestamp}] cpu_avg={cpu_avg:.1f}% gpu={gpu_text}% "
                    f"{cores_col}={cores_above}"
                )
    except KeyboardInterrupt:
        print("\nStopped by user.")

    for timestamp, cpu_avg, gpu_pct, cores_above in rows:
        sheet.append([timestamp, round(cpu_avg, 2), gpu_pct, cores_above])

    workbook.save(output_path)
    print(f"Saved {len(rows)} samples to {output_path}")

    if rows:
        gpu_values = [row[2] for row in rows if row[2] is not None]
        if gpu_values:
            print(
                f"GPU stats: min={min(gpu_values):.1f}% "
                f"max={max(gpu_values):.1f}% "
                f"avg={statistics.fmean(gpu_values):.1f}%"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
