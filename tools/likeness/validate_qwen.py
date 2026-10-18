#!/usr/bin/env python3
"""Evaluate live Qwen responses using the worker's actual prompt, schema and repair.

Synthetic: --synthetic dist/likeness-integrated
Photos: --manifest cases.json (list of {id, images: [paths], expected: {field: [IDs]}}).
Image paths are relative to the manifest. Expected selections are optional and
must be labeled separately; repaired defaults never count as raw model matches.
Reads VLM_BASE_URL, VLM_API_KEY, VLM_MODEL. Writes no images or credentials.
"""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "server/worker"))
import jsonschema
import schema_gen
import spec_ai


class RecordedBackend(spec_ai.OpenAICompatBackend):
    def complete(self, messages, schema):
        self.attempts = []
        self.answer = None
        return super().complete(messages, schema)

    def _post(self, body):
        attempt = {"format": (body.get("response_format") or {}).get("type", "prompt_schema")}
        self.attempts.append(attempt)
        started = time.monotonic()
        try:
            self.answer = super()._post(body)
            return self.answer
        except spec_ai.VLMError as error:
            attempt["error"] = str(error)
            raise
        finally:
            attempt["seconds"] = round(time.monotonic() - started, 3)


def assess(raw, expected):
    errors = sorted(jsonschema.Draft202012Validator(schema_gen.vlm_schema()).iter_errors(raw),
                    key=lambda e: str(list(e.absolute_path)))
    appearance = raw.get("appearance", {}) if isinstance(raw, dict) else {}
    if not isinstance(appearance, dict):
        appearance = {}
    matches = {field: isinstance(appearance.get(field), str) and appearance[field] in allowed
               for field, allowed in expected.items()}
    return {"raw_schema_ok": not errors,
            "schema_errors": [{"path": list(e.absolute_path), "message": e.message} for e in errors],
            "raw_appearance": appearance, "expected": expected, "matches": matches}


def synthetic_cases(batch):
    records = json.loads((batch / "catalog.json").read_text())
    field_for = {"Faces": "face", "Hair": "hair", "Bodies": "body", "Clothes": "outfit"}
    cases = []
    for record in records:
        field = field_for[record["group"]]
        expected = {field: [record["profile"][field]]}
        if record["group"] in ("Faces", "Hair"):
            expected["body"] = ["unknown"]
        cases.append({"id": record["id"], "images": [str((batch / record["front"]).resolve())],
                      "expected": expected, "kind": "synthetic"})
    return cases


def evaluate(case, backend):
    started = time.monotonic()
    result = {"id": case["id"], "kind": case.get("kind", "photo"), "inputs": []}
    result["use_cv"] = result["kind"] != "synthetic"
    photos = []
    for filename in case["images"]:
        data = Path(filename).read_bytes()
        photos.append(data)
        result["inputs"].append({"file": Path(filename).name, "sha256": hashlib.sha256(data).hexdigest()})
    try:
        spec, info = spec_ai.generate_spec(photos, "sglguest", "Evaluation", backend,
                                          require_model=True, use_cv=result["use_cv"], log=lambda _: None)
        raw = spec_ai.parse_json(backend.answer)
        result.update(assess(raw, case.get("expected", {})))
        result.update(raw=raw, spec=spec, repair_notes=info["notes"], samples=info["samples"])
    except Exception as error:
        result.update(error=str(error), raw_schema_ok=False, matches={})
    result["attempts"] = getattr(backend, "attempts", [])
    result["seconds"] = round(time.monotonic() - started, 3)
    return result


def summarize(results):
    fields = {}
    visibility = {"unobservable_body_unknown": {"matched": 0, "labeled": 0},
                  "visible_body_profile": {"matched": 0, "labeled": 0}}
    for result in results:
        for field, match in result.get("matches", {}).items():
            tally = fields.setdefault(field, {"matched": 0, "labeled": 0})
            tally["matched"] += bool(match)
            tally["labeled"] += 1
            if field == "body":
                key = "unobservable_body_unknown" if result.get("expected", {}).get(field) == ["unknown"] else "visible_body_profile"
                visibility[key]["matched"] += bool(match)
                visibility[key]["labeled"] += 1
    return {"cases": len(results), "inference_errors": sum("error" in r for r in results),
            "raw_schema_valid": sum(r["raw_schema_ok"] for r in results), "selection_matches": fields, **visibility,
            "median_seconds": round(statistics.median(r["seconds"] for r in results), 3) if results else None}


def write_report(output, report):
    (output / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    summary = report["summary"]
    lines = ["# Qwen response evaluation", "", f"Model: `{report['model']}`. Started: {report['started_at']}.",
             "", report["scope"], "",
             f"Raw schema-valid responses: {summary['raw_schema_valid']}/{summary['cases']}. "
             f"Inference failures: {summary['inference_errors']}. Median time: {summary['median_seconds']} s.",
             "", "Label agreement uses raw model selections, before repair. Unlabeled fields have no accuracy score.",
             "", "| Case | Raw schema | Face | Hair | Body | Outfit | Label agreement | Seconds |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]
    for result in report["results"]:
        appearance = result.get("raw_appearance", {})
        # Values come from model responses; keep arbitrary text out of table syntax.
        def cell(value):
            return str(value).replace("|", "/").replace("\n", " ").replace("\r", " ")
        selections = " | ".join(cell(appearance.get(k, "—")) for k in ("face", "hair", "body", "outfit"))
        matches = "; ".join(f"{k}: {'match' if v else 'MISS'}" for k, v in result.get("matches", {}).items())
        lines.append(f"| {cell(result['id'])} | {'pass' if result['raw_schema_ok'] else 'FAIL'} | {selections} | {matches or 'unlabeled'} | {result['seconds']} |")
    (output / "report.md").write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--synthetic", type=Path)
    source.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--only", nargs="+")
    args = parser.parse_args()
    if args.synthetic:
        cases = synthetic_cases(args.synthetic.resolve())
    else:
        cases = json.loads(args.manifest.read_text())
        for case in cases:
            case["images"] = [str((args.manifest.resolve().parent / p).resolve()) for p in case["images"]]
    if args.only:
        missing = set(args.only) - {c["id"] for c in cases}
        if missing:
            parser.error(f"unknown case IDs: {sorted(missing)}")
        cases = [c for c in cases if c["id"] in args.only]
    if not cases:
        parser.error("no evaluation cases")
    for case in cases:
        if not 1 <= len(case["images"]) <= 4:
            parser.error(f"{case['id']}: expected 1–4 images")
        for field, allowed in case.get("expected", {}).items():
            choices = schema_gen.appearance_catalog().PROFILE_DESCRIPTIONS.get(field, {})
            if not choices or not isinstance(allowed, list) or not allowed or any(v not in [*choices, "unknown"] for v in allowed):
                parser.error(f"{case['id']}: invalid expected selections for {field}")
    backend = RecordedBackend.from_env()
    if backend is None or not backend.model:
        parser.error("set VLM_BASE_URL and VLM_MODEL (and VLM_API_KEY when required)")
    args.output.mkdir(parents=True, exist_ok=True)
    prompt = spec_ai.system_prompt()
    schema = schema_gen.vlm_schema()
    (args.output / "prompt.txt").write_text(prompt)
    (args.output / "schema.json").write_text(json.dumps(schema, indent=2) + "\n")
    results = []
    report = {"model": backend.model, "started_at": datetime.now(timezone.utc).isoformat(),
              "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "scope": ("Synthetic render recognition is not evidence of real-photo likeness." if args.synthetic else
                        "Reference-photo evaluation against manually labeled acceptable selections. "
                        "Repeated views of a subject do not establish accuracy across people.")}
    try:
        for case in cases:
            result = evaluate(case, backend)
            results.append(result)
            report.update(summary=summarize(results), results=results)
            write_report(args.output, report)
            print(json.dumps({k: result.get(k) for k in ("id", "seconds", "raw_schema_ok", "raw_appearance", "matches", "error")}), flush=True)
    finally:
        backend.client.close()
    print(json.dumps(report.get("summary", {})), flush=True)
    if any("error" in r or not r["raw_schema_ok"] or not all(r.get("matches", {}).values()) for r in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
