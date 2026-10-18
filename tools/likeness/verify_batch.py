#!/usr/bin/env python3
"""Check delivered GLBs, shape variation, artifacts, and face/skin colour continuity."""
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys

from PIL import Image

from catalog import entries


def srgb(value):
    return 12.92 * value if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055


def verify(batch):
    records = json.loads((batch / "catalog.json").read_text())
    assert {r["id"] for r in records} == {e["id"] for e in entries()}, "incomplete catalog"
    by_group = {}
    for record in records:
        folder = batch / "models" / record["id"]
        for path in [record["model"], record["poster"], record["front"],
                     f"models/{record['id']}/{record['id']}.blend"]:
            assert (batch / path).is_file(), path
        report = json.loads((folder / "build_report.json").read_text())
        assert report["validation"]["ok"], record["id"]
        data = (batch / record["model"]).read_bytes()
        magic, version, length = struct.unpack_from("<4sII", data)
        assert magic == b"glTF" and version == 2 and length == len(data)
        size, kind = struct.unpack_from("<II", data, 12)
        assert kind == 0x4E4F534A
        gltf = json.loads(data[20:20 + size])
        binary_size, kind = struct.unpack_from("<II", data, 20 + size)
        assert kind == 0x004E4942
        binary = data[28 + size:28 + size + binary_size]
        geometry = hashlib.sha256()
        for mesh in gltf["meshes"]:
            for primitive in mesh["primitives"]:
                accessor = gltf["accessors"][primitive["attributes"]["POSITION"]]
                assert accessor["componentType"] == 5126 and accessor["type"] == "VEC3"
                view = gltf["bufferViews"][accessor["bufferView"]]
                offset = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
                stride = view.get("byteStride", 12)
                for n in range(accessor["count"]):
                    xyz = struct.unpack_from("<fff", binary, offset + stride * n)
                    assert all(math.isfinite(x) for x in xyz), record["id"]
                    geometry.update(struct.pack("<fff", *xyz))
        fingerprints = by_group.setdefault(record["group"], set())
        assert geometry.hexdigest() not in fingerprints, f"duplicate shape in {record['group']}: {record['id']}"
        fingerprints.add(geometry.hexdigest())
        skin = next(m for m in gltf["materials"] if m["name"] == "Browser Skin (SKIN)")
        expected = [round(srgb(c) * 255) for c in skin["pbrMetallicRoughness"]["baseColorFactor"][:3]]
        for name in ("Browser Open Eyes (SKIN)", "Browser Mouth (SKIN)"):
            material = next(m for m in gltf["materials"] if m["name"] == name)
            texture = gltf["textures"][material["pbrMetallicRoughness"]["baseColorTexture"]["index"]]
            image = gltf["images"][texture["source"]]
            view = gltf["bufferViews"][image["bufferView"]]
            start = view.get("byteOffset", 0)
            with Image.open(io.BytesIO(binary[start:start + view["byteLength"]])) as im:
                background = im.convert("RGB").getpixel((0, 0))
            assert max(abs(a - b) for a, b in zip(background, expected)) <= 2, (record["id"], name, background, expected)
        print(f"OK {record['id']} {record['label']}")
    print(f"Verified {len(records)} models: exports, finite/distinct geometry, images, and matching face/skin colors.")


if __name__ == "__main__":
    verify(Path(sys.argv[1] if len(sys.argv) > 1 else "dist/likeness-round-01").resolve())
