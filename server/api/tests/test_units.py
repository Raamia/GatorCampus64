"""No-DB unit tests: names, photo processing, JWKS cache."""
import io

import pytest
from PIL import Image

from sgl_api import images, names
from sgl_api.auth import AuthError, JWKSCache

from .conftest import jpeg, png


@pytest.mark.parametrize("ok", ["Daniel", "Al Bert", "X", "GATOR_64", "Peacock", "Grape", "Cucumber", "Nigel",
                                "Bob", "Sussex Gal"[:12], "Hi-5!"])
def test_names_ok(ok):
    assert names.validate(f"  {ok} ") == ok.strip()


@pytest.mark.parametrize("bad", ["", "   ", "ThirteenChars", "Gât", "tab\there", "a\\#ff0000\\",
                                 "fuck", "FuUuCk", "f.u.c.k", "sh1t", "ass", "big ass", "kkk", "Nazi Gator"])
def test_names_bad(bad):
    with pytest.raises(names.NameInvalid):
        names.validate(bad)


def test_photo_exif_stripped_and_resized():
    src = jpeg(3000, 2000)
    assert b"SecretCam" in src
    out = images.process(src)
    img = Image.open(io.BytesIO(out))
    assert img.format == "JPEG" and max(img.size) == 1024 and img.size == (1024, 683)
    assert b"SecretCam" not in out and not img.getexif() and "exif" not in img.info


def test_photo_exif_orientation_applied():
    img = Image.new("RGB", (400, 200), (1, 2, 3))
    ex = Image.Exif()
    ex[0x0112] = 6  # rotate 90 CW on display
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=ex)
    out = Image.open(io.BytesIO(images.process(buf.getvalue())))
    assert out.size == (200, 400)


def test_photo_png_alpha_flattened_small_kept():
    out = Image.open(io.BytesIO(images.process(png(300, 500))))
    assert out.size == (300, 500) and out.mode == "RGB"


@pytest.mark.parametrize("fmt", ["GIF", "BMP"])
def test_photo_rejects_other_formats(fmt):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, fmt)
    with pytest.raises(images.PhotoError):
        images.process(buf.getvalue())


def test_photo_rejects_garbage():
    with pytest.raises(images.PhotoError):
        images.process(b"\xff\xd8\xff not really a jpeg")


def test_jwks_cache_refetches_unknown_kid_rate_limited(jwks):
    calls = []

    def fetch(url):
        calls.append(url)
        return jwks

    c = JWKSCache("u", fetch=fetch, min_refetch=3600)
    assert c.get("test-kid") is not None
    with pytest.raises(AuthError):
        c.get("other")
    assert len(calls) == 1  # unknown kid within min_refetch does not hammer Auth0
    c2 = JWKSCache("u", fetch=fetch, min_refetch=0)
    c2.get("test-kid")
    with pytest.raises(AuthError):
        c2.get("other")
    assert len(calls) == 3


def test_config_defaults_follow_sgl_domain(monkeypatch):
    from sgl_api import config
    for k in ("SGL_DOMAIN", "AUTH0_ISSUER", "AUTH0_AUDIENCE", "AUTH0_CLAIM_NAMESPACE", "CORS_ORIGINS", "PLAY_ADDRESS"):
        monkeypatch.delenv(k, raising=False)
    s = config.load()
    assert (s.auth0_issuer, s.auth0_audience, s.claim_namespace, s.play_address) == (
        "https://login.gatorcamp.us/", "https://api.gatorcamp.us", "https://gatorcamp.us/", "play.gatorcamp.us:7777")
    assert s.cors_origins == ["https://gatorcamp.us", "https://www.gatorcamp.us"]
    monkeypatch.setenv("SGL_DOMAIN", "example.org")
    monkeypatch.setenv("AUTH0_AUDIENCE", "https://aud.test")
    s = config.load()
    assert s.auth0_issuer == "https://login.example.org/" and s.auth0_audience == "https://aud.test"
    assert s.claim_namespace == "https://example.org/" and s.play_address == "play.example.org:7777"


def test_principal_claim_namespace():
    from sgl_api.auth import Principal
    p = Principal("a|b", set(), {"https://gatorcamp.us/uf": True, "https://gatorcamp.us/nickname": "Gat"})
    assert p.email_uf is True and p.nickname == "Gat"
    q = Principal("a|b", set(), {"https://gatorcamp.us/uf": True}, claim_ns="https://other.test/")
    assert q.email_uf is False
