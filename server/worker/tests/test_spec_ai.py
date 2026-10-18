import io
import json

import httpx
import jsonschema
import numpy as np
import pytest
from PIL import Image

import photo_colors
import schema_gen
import spec_ai

SCHEMA = schema_gen.character_schema()

GOOD = {
    "colors": {"skin": "#D99C7E", "hair": "#1E1C1C", "eyes": "#3B2117", "top": "#38373E",
               "top_detail": "#151417", "pants": "#3B4E6E", "shoes": "#F2F2F2"},
    "outfit": {"top": "black hoodie", "pants": "jeans", "shoes": "white sneakers", "accessory": "bag strap",
               "headwear": "none"},
    "signature_traits": ["heavy straight fringe", "big toothy grin"],
    "build": {"sleeves": "long", "legwear": "long_pants", "hair_style": "straight_fringe_medium",
              "accessories": ["hood_down", "crossbody_strap"]},
}


def synthetic_photo(skin=(200, 150, 120), hair=(30, 25, 20), top=(40, 90, 200), bg=(230, 230, 230),
                    size=(600, 800)):
    """A crude portrait laid out like heuristic_face expects: hair cap, face, shirt."""
    w, h = size
    a = np.zeros((h, w, 3), np.uint8)
    a[:] = bg
    side = 0.42 * min(w, h)
    x0, y0 = int(0.5 * w - side / 2), int(0.40 * h - side / 2)
    a[max(0, y0 - int(0.35 * side)):y0 + int(0.15 * side), x0 - 10:x0 + int(side) + 10] = hair
    a[y0 + int(0.15 * side):y0 + int(side), x0:x0 + int(side)] = skin
    a[y0 + int(1.3 * side):, max(0, x0 - int(0.5 * side)):x0 + int(1.5 * side)] = top
    rng = np.random.default_rng(1)
    noisy = np.clip(a.astype(int) + rng.integers(-6, 7, a.shape), 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(noisy).save(buf, "PNG")
    return buf.getvalue()


# ------------------------------------------------------------------ colour sampling
def test_kmeans_finds_clusters():
    rng = np.random.default_rng(0)
    pts = np.concatenate([rng.normal(c, 3, (n, 3)) for c, n in (((200, 50, 50), 500), ((20, 20, 200), 300),
                                                                 ((240, 240, 240), 100))])
    centers, counts = photo_colors.kmeans(pts, k=3)
    assert list(counts) == sorted(counts, reverse=True)
    assert np.allclose(centers[0], (200, 50, 50), atol=3)
    assert np.allclose(centers[1], (20, 20, 200), atol=3)


def test_sampling_synthetic_photo():
    s = photo_colors.sample_photos([synthetic_photo()], use_cv=False)
    assert s["_faces"] == ["heuristic"]
    assert photo_colors.delta_e(s["skin"], "#C89678") < 5
    assert photo_colors.delta_e(s["hair"], "#1E1914") < 5
    assert photo_colors.delta_e(s["top"], "#285AC8") < 5


def test_sampling_median_over_photos():
    photos = [synthetic_photo(skin=(200, 150, 120)), synthetic_photo(skin=(190, 140, 110)),
              synthetic_photo(skin=(120, 220, 120))]  # an outlier (green light)
    s = photo_colors.sample_photos(photos, use_cv=False)
    assert photo_colors.delta_e(s["skin"], "#BE9678") < 4  # per-channel median


def test_delta_e():
    assert photo_colors.delta_e("#FFFFFF", "#FFFFFF") == 0
    assert photo_colors.delta_e("#000000", "#FFFFFF") == pytest.approx(100, abs=0.1)


# ------------------------------------------------------------------ repair
def test_repair_good_spec_keeps_model_values():
    spec, notes = spec_ai.repair(GOOD, "sglguest", "Daniel", {"skin": "#D09A80", "hair": "#202020"})
    jsonschema.validate(spec, SCHEMA)
    assert spec["id"] == "sglguest" and spec["name"] == "Daniel"
    assert spec["colors"]["skin"] == "#D99C7E"
    assert spec["build"] == GOOD["build"]
    assert spec["colors"]["skin_shadow"] == "#C38C71"  # 0.9 x skin
    assert notes == []


def test_repair_unknown_enums_to_default():
    raw = json.loads(json.dumps(GOOD))
    raw["build"].update(hair_style="mohawk_spiky", sleeves="sleeveless", legwear="skirt",
                        accessories=["glasses_thick_rectangular", "hood_down", "hood_down", "cape", 7])
    spec, notes = spec_ai.repair(raw, "sglguest", "X")
    jsonschema.validate(spec, SCHEMA)
    assert spec["build"]["hair_style"] == schema_gen.default_hair_style()
    assert spec["build"]["sleeves"] == "long"
    assert spec["build"]["legwear"] == "long_pants"
    assert spec["build"]["accessories"] == ["hood_down"]  # _todo stub, dupes and junk dropped
    assert any("hair_style" in n for n in notes)


def test_repair_close_enum_and_case():
    raw = json.loads(json.dumps(GOOD))
    raw["build"].update(hair_style="Straight Fringe Medium", sleeves="SHORT", legwear="shorts ")
    spec, _ = spec_ai.repair(raw, "sglguest", "X")
    assert spec["build"]["hair_style"] == "straight_fringe_medium"
    assert spec["build"]["sleeves"] == "short" and spec["build"]["legwear"] == "shorts"


def test_repair_bad_hex_uses_sample_then_default():
    raw = json.loads(json.dumps(GOOD))
    raw["colors"].update(top="navy blue", hair="#12345", pants=None, shoes="fff")
    spec, notes = spec_ai.repair(raw, "sglguest", "X", {"top": "#203060"})
    jsonschema.validate(spec, SCHEMA)
    assert spec["colors"]["top"] == "#203060"          # sampled
    assert spec["colors"]["hair"] == spec_ai.DEFAULT_COLORS["hair"]  # no sample -> default
    assert spec["colors"]["pants"] == spec_ai.DEFAULT_COLORS["pants"]
    assert spec["colors"]["shoes"] == "#FFFFFF"        # short hex expanded
    assert any("bad hex" in n for n in notes)


def test_repair_replaces_far_off_skin_and_hair():
    raw = json.loads(json.dumps(GOOD))
    raw["colors"].update(skin="#FFE0D0", hair="#E0C040")  # very pale / blond vs dark photos
    spec, notes = spec_ai.repair(raw, "sglguest", "X", {"skin": "#8A5A40", "hair": "#1A1410"})
    assert spec["colors"]["skin"] == "#8A5A40"
    assert spec["colors"]["hair"] == "#1A1410"
    assert spec["colors"]["skin_shadow"] == "#7C513A"  # follows the replaced skin
    assert sum("from the photos" in n for n in notes) == 2


def test_repair_close_colours_kept():
    spec, _ = spec_ai.repair(GOOD, "sglguest", "X", {"skin": "#C99080", "hair": "#303030"})
    assert spec["colors"]["skin"] == "#D99C7E" and spec["colors"]["hair"] == "#1E1C1C"


def test_repair_text_limits_and_garbage():
    raw = json.loads(json.dumps(GOOD))
    raw["outfit"]["top"] = "x" * 500 + "\n\x00"
    raw["outfit"]["cape"] = "red"
    raw["signature_traits"] = ["a", "a", None, "b\tc", "d", "e", "f", "g", "h"]
    raw["id"] = "daniel"  # the model can't pick the id
    raw["based_on"] = "daniel"
    spec, _ = spec_ai.repair(raw, "sglguest", "Name\x07That is way too long for a name field ok", None)
    jsonschema.validate(spec, SCHEMA)
    assert len(spec["outfit"]["top"]) == 200 and "cape" not in spec["outfit"]
    assert spec["signature_traits"] == ["a", "b c", "d", "e", "f", "g"]
    assert spec["id"] == "sglguest" and "based_on" not in spec
    assert len(spec["name"]) <= 32


def test_repair_nothing():
    spec, notes = spec_ai.repair(None, "sglguest", "Nobody", {"skin": "#A07050"})
    jsonschema.validate(spec, SCHEMA)
    assert spec["colors"]["skin"] == "#A07050"
    assert spec["build"]["hair_style"] == schema_gen.default_hair_style()


def test_parse_json_fenced():
    assert spec_ai.parse_json('Sure!\n```json\n{"a": 1}\n```') == {"a": 1}
    assert spec_ai.parse_json('{"a": {"b": 2}} trailing') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        spec_ai.parse_json("no json here")


# ------------------------------------------------------------------ generate_spec + backends
def test_generate_spec_with_static_backend():
    photo = synthetic_photo()
    raw = json.loads(json.dumps(GOOD))
    raw["colors"]["skin"] = "#3A2010"  # far off the synthetic photo's skin
    backend = spec_ai.StaticBackend("```json\n" + json.dumps(raw) + "\n```")
    logs = []
    spec, info = spec_ai.generate_spec([photo], "sglguest", "Pat", backend, use_cv=False, log=logs.append)
    jsonschema.validate(spec, SCHEMA)
    assert photo_colors.delta_e(spec["colors"]["skin"], "#C89678") < 5
    messages, schema = backend.calls[0]
    assert schema == schema_gen.vlm_schema()
    assert messages[1]["content"][1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "straight_fringe_medium" in messages[0]["content"]


def test_generate_spec_model_failure_falls_back():
    class Broken:
        def complete(self, messages, schema):
            raise spec_ai.VLMError("HTTP 500")
    spec, info = spec_ai.generate_spec([synthetic_photo()], "sglguest", "Pat", Broken(), use_cv=False,
                                       log=lambda m: None)
    jsonschema.validate(spec, SCHEMA)
    with pytest.raises(spec_ai.VLMError):
        spec_ai.generate_spec([synthetic_photo()], "sglguest", "Pat", Broken(), use_cv=False,
                              require_model=True, log=lambda m: None)


def test_openai_backend_falls_back_on_response_format():
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body.get("response_format", {}).get("type"))
        assert request.headers["authorization"] == "Bearer k"
        if body.get("response_format", {}).get("type") == "json_schema":
            return httpx.Response(400, json={"error": "response_format json_schema not supported"})
        return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(GOOD)}}]})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    b = spec_ai.OpenAICompatBackend("http://vlm/v1/", "k", "m", client=client)
    out = b.complete([{"role": "system", "content": "s"}, {"role": "user", "content": "u"}], {"type": "object"})
    assert json.loads(out) == GOOD
    assert seen == ["json_schema", "json_object"]


def test_openai_backend_server_error_is_final():
    calls = []

    def handler(request):
        calls.append(1)
        return httpx.Response(503, text="overloaded")

    b = spec_ai.OpenAICompatBackend("http://vlm/v1", client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(spec_ai.VLMError):
        b.complete([{"role": "system", "content": "s"}], {})
    assert len(calls) == 1


@pytest.mark.parametrize('content', [None, '', '   ', '{"colors": broken JSON'])
def test_openai_backend_retries_http_200_unusable_content(content):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body.get('response_format', {}).get('type'))
        answer = content if len(seen) == 1 else json.dumps(GOOD)
        return httpx.Response(200, json={'choices': [{'message': {'content': answer}}]})

    backend = spec_ai.OpenAICompatBackend('http://vlm/v1', client=httpx.Client(transport=httpx.MockTransport(handler)))
    output = backend.complete([{'role': 'system', 'content': 's'}], schema_gen.vlm_schema())
    assert json.loads(output) == GOOD
    assert seen == ['json_schema', 'json_object']


def test_openai_backend_limits_unusable_content_retries_without_logging_content():
    seen = []
    sensitive = 'not JSON: private user description'

    def handler(request):
        body = json.loads(request.content)
        seen.append(body.get('response_format', {}).get('type'))
        return httpx.Response(200, json={'choices': [{'message': {'content': sensitive}}]})

    backend = spec_ai.OpenAICompatBackend('http://vlm/v1', client=httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(spec_ai.VLMError, match='formats exhausted') as error:
        backend.complete([{'role': 'system', 'content': 's'}], schema_gen.vlm_schema())
    assert seen == ['json_schema', 'json_object', None]
    assert sensitive not in str(error.value)


def test_openai_backend_strips_transport_unique_items_preserves_local_validation():
    schema = schema_gen.vlm_schema()
    original = json.dumps(schema, sort_keys=True)
    assert schema['properties']['build']['properties']['accessories']['uniqueItems'] is True

    def handler(request):
        body = json.loads(request.content)
        sent = body['response_format']['json_schema']['schema']
        assert 'uniqueItems' not in json.dumps(sent)
        assert sent['properties']['build']['properties']['accessories']['items'] == schema['properties']['build']['properties']['accessories']['items']
        return httpx.Response(200, json={'choices': [{'message': {'content': json.dumps(GOOD)}}]})

    backend = spec_ai.OpenAICompatBackend('http://vlm/v1', client=httpx.Client(transport=httpx.MockTransport(handler)))
    backend.complete([{'role': 'system', 'content': 's'}], schema)
    assert json.dumps(schema, sort_keys=True) == original
    duplicate = json.loads(json.dumps(GOOD))
    duplicate['build']['accessories'] = ['hood_down', 'hood_down']
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(duplicate, schema)
