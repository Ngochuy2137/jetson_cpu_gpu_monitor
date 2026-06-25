# Jetson CPU/GPU Monitor

Log CPU and GPU usage to an Excel file. CPU sampling uses the same approach as
`main_controller` (`psutil.cpu_percent(interval=0, percpu=True)`).

## Install

```bash
pip install -r requirements.txt
```

For the optional GPU stress utility, CUDA `nvcc` must be available
(`/usr/local/cuda/bin`).

## Monitor

```bash
python3 monitor.py --hz 10 --threshold 80 --duration 60 -o output.xlsx
```

| Argument | Default | Description |
|----------|---------|-------------|
| `--hz` | `10` | Sampling rate (Hz) |
| `-x`, `--threshold` | `80` | Count CPU cores above this usage (%) |
| `--duration` | `0` | Run time in seconds (`0` = until Ctrl+C) |
| `-o`, `--output` | auto timestamp | Output `.xlsx` path |

### Excel columns

| Column | Description |
|--------|-------------|
| `timestamp` | Local time with milliseconds |
| `cpu_avg_pct` | Average CPU usage across all cores |
| `gpu_pct` | Jetson GPU load from sysfs (`/10`) |
| `cores_above_{x}pct` | Number of cores with usage > `x` |

## GPU stress (for testing)

```bash
python3 gpu_stress.py
```

## Quick test

```bash
./run_test.sh
```

Runs GPU stress in the background and records 15 seconds at 10 Hz.
