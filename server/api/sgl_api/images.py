"""Photo intake: JPEG/PNG only (sniffed by content), EXIF stripped, longest side ≤ 1024, re-encoded JPEG."""
from __future__ import annotations

import io

from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard (a 8 MB PNG can't legitimately exceed this)
# iPhone HDR JPEGs may contain an MPF gain map and be identified as MPO.
# Decode only the primary JPEG; auxiliary images never enter the pipeline.
ALLOWED = {"JPEG", "PNG", "MPO"}


class PhotoError(ValueError):
    pass


def process(data: bytes, max_side: int = 1024) -> bytes:
    """Return a clean JPEG: orientation applied, all metadata (EXIF/GPS/XMP/ICC text) dropped."""
    try:
        with Image.open(io.BytesIO(data)) as probe:
            fmt = probe.format
            probe.verify()
        if fmt not in ALLOWED:
            raise PhotoError(f"only JPEG or PNG photos are accepted (got {fmt or 'unknown'})")
        with Image.open(io.BytesIO(data)) as source:
            source.seek(0)
            source.load()
            img = ImageOps.exif_transpose(source)
    except PhotoError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as e:
        raise PhotoError("photo is too large") from e
    except Exception as e:  # noqa: BLE001 - PIL raises many types for corrupt files
        raise PhotoError("not a readable JPEG or PNG") from e

    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.getchannel("A"))
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    if max(img.size) > max_side:
        img.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
    # A fresh image object carries no info dict, so nothing from the original survives.
    clean = Image.new("RGB", img.size)
    clean.paste(img)
    out = io.BytesIO()
    clean.save(out, format="JPEG", quality=90, optimize=True)
    return out.getvalue()
