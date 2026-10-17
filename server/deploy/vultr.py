#!/usr/bin/env python3
"""Tiny Vultr API v2 client for provisioning sgl64 infrastructure.

Reads the API key from ~/.config/sgl64/vultr.env (either the bare key or VULTR_API_KEY=...).
Usage: server/deploy/vultr.py GET /instances
       server/deploy/vultr.py POST /databases '{"database_engine": "pg", ...}'
       server/deploy/vultr.py PATCH /instances/<id> '{"plan": "..."}'
Prints the JSON response. Never prints the key.
"""
import json
import os
import sys
import urllib.error
import urllib.request

KEY_FILE = os.path.expanduser("~/.config/sgl64/vultr.env")


def api_key():
    raw = open(KEY_FILE).read().strip()
    return raw.split("=", 1)[1].strip() if raw.startswith("VULTR_API_KEY=") else raw


def call(method, path, body=None):
    req = urllib.request.Request(
        "https://api.vultr.com/v2" + path,
        method=method,
        data=json.dumps(body).encode() if body is not None else None,
        headers={"Authorization": "Bearer " + api_key(), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            text = resp.read().decode()
            return resp.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return e.code, json.loads(text)
        except ValueError:
            return e.code, {"error": text}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    status, data = call(sys.argv[1].upper(), sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else None)
    print(json.dumps(data, indent=2))
    sys.exit(0 if status < 400 else 1)
