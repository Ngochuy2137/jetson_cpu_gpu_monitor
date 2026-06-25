#!/usr/bin/env python3
"""Run a continuous CUDA workload to load the Jetson GPU."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

PACKAGE_DIR = Path(__file__).resolve().parent
CU_SOURCE = PACKAGE_DIR / "gpu_stress.cu"
BINARY = PACKAGE_DIR / "gpu_stress_test"


def find_nvcc() -> str | None:
    for candidate in (
        shutil.which("nvcc"),
        "/usr/local/cuda/bin/nvcc",
    ):
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


def build_binary() -> Path:
    nvcc = find_nvcc()
    if not nvcc:
        raise RuntimeError("nvcc not found. Install CUDA toolkit or add /usr/local/cuda/bin to PATH.")

    cmd = [nvcc, "-O2", str(CU_SOURCE), "-o", str(BINARY)]
    print(f"Building GPU stress binary: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    return BINARY


def ensure_binary() -> Path:
    if BINARY.is_file() and BINARY.stat().st_mtime >= CU_SOURCE.stat().st_mtime:
        return BINARY
    return build_binary()


def main() -> int:
    parser = argparse.ArgumentParser(description="Continuous CUDA GPU stress for monitoring tests.")
    parser.add_argument(
        "--iterations-per-loop",
        type=int,
        default=500,
        help="CUDA kernel launch batches per loop (default: 500)",
    )
    args = parser.parse_args()

    try:
        binary = ensure_binary()
    except (RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Failed to build GPU stress binary: {exc}", file=sys.stderr)
        return 1

    print(f"Starting GPU stress ({binary.name}), Ctrl+C to stop.")
    while True:
        proc = subprocess.run([str(binary), str(args.iterations_per_loop)])
        if proc.returncode != 0:
            return proc.returncode


if __name__ == "__main__":
    raise SystemExit(main())
