#!/bin/sh
# Create the managed services for sgl64 on Vultr. Secrets in the responses go to
# ~/.config/sgl64/<name>.json (mode 600), never to the terminal.
# Usage: server/deploy/create_managed.sh db|objects
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT_DIR="$HOME/.config/sgl64"
VPC_ID="e716d656-f06c-4c86-b3c2-f3e26b3c61ae"   # gatorlator, atl, 10.6.96.0/20

case "${1:-}" in
  db)
    name=db
    body='{"database_engine": "pg", "database_engine_version": "17", "region": "atl",
           "plan": "vultr-dbaas-hobbyist-cc-1-25-1", "label": "sgl-db", "vpc_id": "'"$VPC_ID"'",
           "trusted_ips": ["64.177.55.205/32", "64.177.55.146/32", "10.6.96.0/20"]}'
    path=/databases ;;
  objects)
    name=objects
    body='{"cluster_id": 22, "tier_id": 2, "label": "sgl-objects"}'   # atl2, Standard tier
    path=/object-storage ;;
  *) echo "usage: $0 db|objects" >&2; exit 2 ;;
esac

mkdir -p "$OUT_DIR"
out="$OUT_DIR/$name.json"
umask 077
body="$(printf '%s' "$body" | tr '\n' ' ')"
if "$HERE/vultr.py" POST "$path" "$body" > "$out"; then
    chmod 600 "$out"
    echo "created $name; details saved to $out"
else
    chmod 600 "$out"
    echo "failed to create $name; error:" >&2
    python3 -c 'import json,sys; print(json.load(open(sys.argv[1])).get("error"))' "$out" >&2
    exit 1
fi
