#!/usr/bin/env python3
"""Small, dependency-free readiness probe for an OpenAI-compatible VLM.

Usage (inside the worker compose network):
    python vlm_probe.py

The probe only queries /health and /v1/models; it never sends a prompt or image.
It exits 0 only when the endpoint is reachable and advertises the configured
model (or at least one model when VLM_MODEL is unset).
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request


def get(url: str, key: str | None = None) -> tuple[int, object]:
    headers = {"Authorization": f"Bearer {key}"} if key else {}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=float(os.getenv("VLM_PROBE_TIMEOUT", "5"))) as r:
        raw = r.read()
        try:
            return r.status, json.loads(raw)
        except json.JSONDecodeError:
            return r.status, raw.decode("utf-8", "replace")


def main() -> int:
    base = os.getenv("VLM_BASE_URL", "http://vllm:8000/v1").rstrip("/")
    key = os.getenv("VLM_API_KEY")
    try:
        status, _ = get(base.removesuffix("/v1") + "/health", key)
        if status != 200:
            raise RuntimeError(f"health returned HTTP {status}")
        status, payload = get(base + "/models", key)
        ids = [m.get("id") for m in payload.get("data", [])] if isinstance(payload, dict) else []
        wanted = os.getenv("VLM_MODEL")
        if not ids or (wanted and wanted not in ids):
            raise RuntimeError(f"models={ids!r}, expected {wanted!r}")
        print(f"VLM ready: {', '.join(ids)}")
        return 0
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"VLM not ready: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
