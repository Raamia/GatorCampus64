"""Best-effort local GPU snapshots. Never contacts the model endpoint or a remote host."""
import csv
from datetime import datetime, timezone
import io
import math
import subprocess

COMMAND = ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total,name",
           "--format=csv,noheader"]
TIMEOUT_SECONDS = 2


def _number(value, unit):
    value = value.strip().removesuffix(unit).strip()
    if value in ("N/A", "[N/A]", "[Not Supported]"):
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError("invalid GPU metric")
    return number


def capture(point):
    """Return JSON-safe evidence, including explicit unavailability on CPU-only machines.

    These are host-wide snapshots, not process attribution or peak measurements.
    Keep error text fixed: subprocess stderr can contain host-specific details.
    """
    sample = {"timestamp": datetime.now(timezone.utc).isoformat(), "point": point,
              "available": False, "gpus": []}
    try:
        result = subprocess.run(COMMAND, capture_output=True, text=True, check=True,
                                timeout=TIMEOUT_SECONDS)
        gpus = []
        for row in csv.reader(io.StringIO(result.stdout), skipinitialspace=True):
            if len(row) != 4 or not row[3].strip():
                raise ValueError("invalid GPU row")
            utilization, used, total = (_number(row[0], "%"), _number(row[1], "MiB"),
                                        _number(row[2], "MiB"))
            if utilization is not None and utilization > 100:
                raise ValueError("invalid utilization")
            gpus.append({"utilization_gpu_pct": utilization, "memory_used_mib": used,
                         "memory_total_mib": total, "name": row[3].strip()})
        if not gpus:
            raise ValueError("empty GPU output")
        sample.update(available=True, gpus=gpus)
    except FileNotFoundError:
        sample["note"] = "GPU telemetry unavailable: nvidia-smi not installed"
    except subprocess.TimeoutExpired:
        sample["note"] = "GPU telemetry unavailable: nvidia-smi timed out"
    except Exception:  # Diagnostics must never turn a successful build into a failure.
        sample["note"] = "GPU telemetry unavailable: query failed or returned invalid output"
    return sample
