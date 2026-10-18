"""Step 2 (spec): photos -> character.json with a vision model, then validate + repair.

Backend: any OpenAI-compatible chat-completions endpoint that takes image inputs
(Vultr Serverless Inference if it has a vision model, or a local vLLM server):
  VLM_BASE_URL   e.g. http://vllm:8000/v1  or the Vultr inference base URL
  VLM_API_KEY    bearer token (any string for a local vLLM)
  VLM_MODEL      e.g. Qwen/Qwen2.5-VL-7B-Instruct-AWQ
  VLM_TIMEOUT    seconds (default 120)
Structured output is requested with response_format json_schema; servers that reject it
are retried with json_object, then with the schema in the prompt only. The answer is never
trusted: repair() makes it schema-clean whatever comes back (or nothing, see generate_spec).

`id` and `name` are set by the worker, never by the model.
"""
import base64
import copy
import difflib
import io
import json
import os
import re
import string

import jsonschema
from PIL import Image, ImageOps

import photo_colors
import schema_gen

# a model colour further than this (CIE76 dE) from the photo sample is replaced by the sample
SKIN_MAX_DE = 22.0
HAIR_MAX_DE = 35.0
SKIN_SHADOW = 0.90       # skin_shadow = skin * 0.90 (the friends' specs use 0.89-0.91)
SHOE_SOLES = 0.88
DEFAULT_COLORS = {"skin": "#C99A7A", "hair": "#2A221E", "eyes": "#3B2117", "top": "#4A6FA5",
                  "pants": "#3B4E6E", "shoes": "#F2F2F2"}
IMAGE_SIDE = 768  # longest side sent to the model (about 600 visual tokens each for Qwen2.5-VL)

ACCESSORY_HINTS = {
    "shirt_collar": "a collared shirt (polo, button-up) with a visible fold-down collar",
    "rolled_cuffs": "short sleeves rolled up into thick cuffs (rare; only if obvious)",
    "hood_down": "a hoodie whose hood rests down behind the neck",
    "crossbody_strap": "a bag strap worn diagonally across the chest",
}


class VLMError(RuntimeError):
    pass


class _InvalidModelOutput(VLMError):
    """A successful transport response that cannot be used as a character spec."""


def _transport_schema(value):
    """Keep local validation strict while avoiding unsupported vLLM guidance keywords."""
    if isinstance(value, dict):
        return {key: _transport_schema(item) for key, item in value.items() if key != "uniqueItems"}
    if isinstance(value, list):
        return [_transport_schema(item) for item in value]
    return value


# ------------------------------------------------------------------ prompt
def system_prompt():
    acc = "\n".join(f"  - {a}: {ACCESSORY_HINTS.get(a, a.replace('_', ' '))}" for a in schema_gen.accessories())
    catalog = schema_gen.appearance_catalog()
    appearance = "\n".join(
        f"appearance.{field}:\n" + "\n".join(f"  - {key}: {description}" for key, description in choices.items())
        for field, choices in catalog.PROFILE_DESCRIPTIONS.items())
    return f"""You design characters for Super Gatorlator 64, a Nintendo 64 style game with
low-poly, chunky, friendly cartoon characters. You get 1-4 photos of ONE real person and
describe them as a character spec. Output ONLY a JSON object that matches the given schema.

Rules:
- colors: #RRGGBB hex. Judge colours under neutral light (ignore shadows, warm lamps, filters).
  skin = the face's mid tone; hair = the dominant hair colour; top = the main clothing colour
  above the waist; pants = what is worn on the legs (guess plain dark jeans #3B4E6E if not
  visible); shoes = shoe colour (#F2F2F2 if not visible).
- Pick independent face, hair, body and outfit profiles from the approved catalog below.
  Use "unknown" for any feature that is obscured, cropped out, or cannot be judged.
  Judge face shape from the visible face outline, not the hairstyle. Judge body only
  from a sufficiently visible silhouette; a headshot or a loose coat does not reveal it.
  If the waist and hips are outside the image, appearance.body MUST be "unknown".
  "neutral" describes visible balanced proportions; it is not an uncertainty default.
  Do not infer body shape from face shape. Hair color comes from colors.hair.
  These are stylized visual matches, not measurements or claims about the person.
{appearance}
- build.legwear: long_pants or shorts. The selected outfit supplies sleeves, collar
  and hood geometry; do not add a collar to a hoodie or a hood to a collared shirt.
- build.accessories: only from this list, only when clearly visible, else []:
{acc}
- outfit: one short phrase each (top, pants, shoes, accessory, headwear; "none" if nothing).
- signature_traits: 2-5 short phrases about what makes this person recognisable
  (hair shape and fringe, smile, glasses, facial hair, eyebrows). Describe appearance only;
  never guess identity, age, ethnicity or anything sensitive. Describe visible features
  directly without inferring gender or pronouns.
"""


def _encode_image(data):
    im = Image.open(io.BytesIO(data))
    im = ImageOps.exif_transpose(im).convert("RGB")
    im.thumbnail((IMAGE_SIDE, IMAGE_SIDE))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=88)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def build_messages(photos):
    content = [{"type": "text", "text": f"{len(photos)} photo(s) of the person. Write their character spec."}]
    for p in photos:
        content.append({"type": "image_url", "image_url": {"url": _encode_image(p)}})
    return [{"role": "system", "content": system_prompt()}, {"role": "user", "content": content}]


# ------------------------------------------------------------------ backends
class OpenAICompatBackend:
    """POST {base_url}/chat/completions with images as data URLs."""

    def __init__(self, base_url, api_key="", model="", timeout=120.0, client=None):
        import httpx
        self.url = base_url.rstrip("/") + "/chat/completions"
        self.model = model
        self.headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = client or httpx.Client(timeout=timeout)

    @classmethod
    def from_env(cls):
        base = os.environ.get("VLM_BASE_URL")
        if not base:
            return None
        return cls(base, os.environ.get("VLM_API_KEY", ""), os.environ.get("VLM_MODEL", ""),
                   float(os.environ.get("VLM_TIMEOUT", "120")))

    def _post(self, body):
        r = self.client.post(self.url, json=body, headers=self.headers)
        if r.status_code >= 400:
            raise VLMError(f"HTTP {r.status_code}")
        try:
            content = r.json()["choices"][0]["message"]["content"]
        except (KeyError, IndexError, ValueError, TypeError) as e:
            raise _InvalidModelOutput("unexpected vision response envelope") from e
        if not isinstance(content, str) or not content.strip():
            raise _InvalidModelOutput("empty or non-text vision response")
        return content

    def complete(self, messages, schema):
        base = {"model": self.model, "messages": messages, "temperature": 0.2, "max_tokens": 1200}
        transport_schema = _transport_schema(schema)
        formats = [
            {"type": "json_schema", "json_schema": {"name": "character_spec", "schema": transport_schema, "strict": True}},
            {"type": "json_object"},
            None,
        ]
        errors = []
        for fmt in formats:
            body = dict(base)
            if fmt is None:
                body["messages"] = copy.deepcopy(messages)
                body["messages"][0]["content"] += "\nJSON schema:\n" + json.dumps(schema)
            else:
                body["response_format"] = fmt
            try:
                text = self._post(body)
                try:
                    parse_json(text)
                except (ValueError, TypeError) as e:
                    raise _InvalidModelOutput("vision response is not a JSON object") from e
                return text
            except VLMError as e:
                # Some vLLM guidance failures return HTTP 200 with empty/invalid content.
                # Retry each weaker format once; server/network failures remain final.
                if not isinstance(e, _InvalidModelOutput) and "HTTP 4" not in str(e):
                    raise
                errors.append(str(e))
        raise VLMError("vision formats exhausted: " + "; ".join(errors))


class StaticBackend:
    """Returns a fixed answer (tests, or VLM_BASE_URL unset in dev)."""

    def __init__(self, answer):
        self.answer = answer if isinstance(answer, str) else json.dumps(answer)
        self.calls = []

    def complete(self, messages, schema):
        self.calls.append((messages, schema))
        return self.answer


def parse_json(text):
    """The model's JSON object (tolerates code fences and prose around it)."""
    text = text.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    if m:
        text = m.group(1)
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no JSON object in the model output")
    return json.loads(text[start:end + 1])


# ------------------------------------------------------------------ repair
_PRINTABLE = set(string.printable) - set("\t\n\r\x0b\x0c")


def clean_text(value, limit=schema_gen.TEXT_MAX):
    if not isinstance(value, str):
        return None
    s = "".join(ch if ch in _PRINTABLE else " " for ch in value)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:limit].rstrip() or None


def _norm_hex(value):
    if isinstance(value, str):
        v = value.strip()
        if re.fullmatch(r"#?[0-9A-Fa-f]{6}", v):
            return "#" + v.lstrip("#").upper()
        if re.fullmatch(r"#?[0-9A-Fa-f]{3}", v):
            return "#" + "".join(c * 2 for c in v.lstrip("#")).upper()
    return None


def _shade(h, f):
    r, g, b = photo_colors.hex_to_rgb(h)
    return photo_colors.rgb_to_hex((r * f, g * f, b * f))


def _enum(value, allowed, default, notes, field):
    if isinstance(value, str):
        v = value.strip().lower().replace(" ", "_").replace("-", "_")
        if v in allowed:
            return v
        close = difflib.get_close_matches(v, allowed, n=1, cutoff=0.85)
        if close:
            notes.append(f"{field}: {value!r} -> {close[0]!r} (closest)")
            return close[0]
    notes.append(f"{field}: {value!r} not allowed -> {default!r}")
    return default


def repair(raw, char_id, name, samples=None):
    """Any model output (dict, or None when the model failed) -> (schema-clean spec, notes).
    samples: photo_colors.sample_photos() output (skin/hair/top) or None."""
    raw = raw if isinstance(raw, dict) else {}
    samples = samples or {}
    notes = []
    # A guessed portrait crop can land on a shirt/background in a full-body
    # photo. Keep those samples as missing-color fallbacks, never as evidence
    # that an otherwise valid model color is wrong. Explicit caller samples
    # without detector metadata retain their existing trusted behavior.
    trusted_samples = "_faces" not in samples or "haar" in samples["_faces"]

    appearance = None
    if "appearance" in raw:
        catalog = schema_gen.appearance_catalog()
        source = raw["appearance"] if isinstance(raw["appearance"], dict) else {}
        appearance = {"version": catalog.VERSION}
        for field, choices in catalog.PROFILE_DESCRIPTIONS.items():
            appearance[field] = _enum(source.get(field), list(choices), catalog.DEFAULTS[field], notes,
                                      f"appearance.{field}")

    # build
    b = raw.get("build") if isinstance(raw.get("build"), dict) else {}
    build = {
        "sleeves": (catalog.OUTFITS[appearance["outfit"]]["sleeves"] if appearance else
                    _enum(b.get("sleeves"), schema_gen.SLEEVES, schema_gen.DEFAULT_SLEEVES, notes, "build.sleeves")),
        "legwear": _enum(b.get("legwear"), schema_gen.LEGWEAR, schema_gen.DEFAULT_LEGWEAR, notes, "build.legwear"),
        "hair_style": (schema_gen.default_hair_style() if appearance else
                       _enum(b.get("hair_style"), schema_gen.hair_styles(), schema_gen.default_hair_style(), notes,
                             "build.hair_style")),
    }
    allowed_acc = schema_gen.accessories()
    acc = []
    for a in b.get("accessories") or [] if isinstance(b.get("accessories"), list) else []:
        if isinstance(a, str) and a in allowed_acc and a not in acc:
            acc.append(a)
        else:
            notes.append(f"build.accessories: dropped {a!r}")
    if "rolled_cuffs" in acc and build["sleeves"] != "short":
        acc.remove("rolled_cuffs")
        notes.append("build.accessories: rolled_cuffs needs short sleeves, dropped")
    build["accessories"] = acc

    # colours: model value, else photo sample, else default; skin/hair cross-checked
    c = raw.get("colors") if isinstance(raw.get("colors"), dict) else {}
    colors = {}
    for key in schema_gen.COLOR_KEYS:
        v = _norm_hex(c.get(key))
        if c.get(key) is not None and v is None:
            notes.append(f"colors.{key}: bad hex {c.get(key)!r}")
        if v is None and key in samples:
            v = samples[key]
            notes.append(f"colors.{key}: sampled {v}")
        if v is None and key in DEFAULT_COLORS:
            v = DEFAULT_COLORS[key]
            notes.append(f"colors.{key}: default {v}")
        if v is not None:
            colors[key] = v
    for key, limit in (("skin", SKIN_MAX_DE), ("hair", HAIR_MAX_DE)):
        if key in samples and key in colors and colors[key] != samples[key]:
            de = photo_colors.delta_e(colors[key], samples[key])
            if de > limit:
                if trusted_samples:
                    notes.append(f"colors.{key}: model {colors[key]} is dE {de:.0f} from the photos, using {samples[key]}")
                    colors[key] = samples[key]
                else:
                    notes.append(f"colors.{key}: keeping model {colors[key]}; heuristic sample {samples[key]} has no detected face")
    # derived shades follow the (possibly replaced) base colour unless the model gave sane ones
    if "skin_shadow" not in colors or photo_colors.delta_e(colors["skin_shadow"], colors["skin"]) > 15:
        colors["skin_shadow"] = _shade(colors["skin"], SKIN_SHADOW)
    colors.setdefault("top_detail", _shade(colors["top"], 0.8))
    colors.setdefault("shoe_soles", _shade(colors["shoes"], SHOE_SOLES))

    # text
    o = raw.get("outfit") if isinstance(raw.get("outfit"), dict) else {}
    outfit = {k: t for k in schema_gen.OUTFIT_KEYS if (t := clean_text(o.get(k)))}
    traits = []
    for t in raw.get("signature_traits") or [] if isinstance(raw.get("signature_traits"), list) else []:
        t = clean_text(t)
        if t and t not in traits:
            traits.append(t)
    traits = traits[:schema_gen.MAX_TRAITS]

    spec = {"id": char_id, "name": clean_text(name, 32) or char_id, "colors": colors, "outfit": outfit,
            "signature_traits": traits, "build": build}
    if appearance:
        spec["appearance"] = appearance
        resolved = catalog.resolve_spec(spec)
        if resolved["build"] != spec["build"]:
            notes.append("build.accessories: fitted to selected appearance.outfit")
        spec = resolved
    jsonschema.validate(spec, schema_gen.character_schema())  # repair bug if this fails
    return spec, notes


# ------------------------------------------------------------------ step entry point
def generate_spec(photos, char_id, name, backend=None, use_cv=True, require_model=False, log=print):
    """photos: list of image bytes. Returns (spec, info) where info has the raw model answer,
    the photo samples and the repair notes. A model failure falls back to a sampled-colour
    default spec unless require_model (then VLMError, including a missing backend)."""
    if require_model and backend is None:
        raise VLMError("vision model required but not configured: set VLM_BASE_URL")
    info = {"model": None, "notes": []}
    try:
        samples = photo_colors.sample_photos(photos, use_cv=use_cv)
    except Exception as e:  # noqa: BLE001 - a broken photo must not kill the job here
        log(f"spec: colour sampling failed: {e}")
        samples = {}
    info["samples"] = samples
    log(f"spec: photo samples {json.dumps({k: v for k, v in samples.items()})}")
    raw = None
    if backend is not None:
        try:
            text = backend.complete(build_messages(photos), schema_gen.vlm_schema())
            info["model"] = text[:4000]
            raw = parse_json(text)
            try:
                jsonschema.validate(raw, schema_gen.vlm_schema())
                log("spec: model output is schema-clean")
            except jsonschema.ValidationError as e:
                log(f"spec: model output not schema-clean ({e.message[:160]}), repairing")
        except Exception as e:  # noqa: BLE001
            if require_model:
                raise VLMError(f"vision model failed: {e}") from e
            log(f"spec: vision model failed ({e}); using photo samples and defaults")
    else:
        log("spec: no vision model configured (VLM_BASE_URL); using photo samples and defaults")
    spec, notes = repair(raw, char_id, name, samples)
    info["notes"] = notes
    for n in notes:
        log("spec: repair: " + n)
    return spec, info
