"""JSON-in / JSON-out entry points (CLI, Pyodide web worker, other agents)."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from phd_matcher.admission.estimator import DEFAULT_SAMPLES, estimate_portfolio
from phd_matcher.admission.models import AdmissionApplicant, AdmissionTarget


def _format_validation(prefix: str, err: ValidationError) -> list[str]:
    out = []
    for e in err.errors():
        loc = ".".join(str(x) for x in e.get("loc", ()))
        out.append(f"{prefix}{'.' + loc if loc else ''}: {e.get('msg', 'invalid')}")
    return out


def estimate_from_dicts(
    applicant: dict,
    targets: list[dict],
    *,
    data_dir: str | Path | None = None,
    samples: int = DEFAULT_SAMPLES,
    with_levers: bool = True,
) -> dict:
    errors: list[str] = []
    try:
        app = AdmissionApplicant(**applicant)
    except ValidationError as e:
        errors.extend(_format_validation("applicant", e))
        app = None
    parsed: list[AdmissionTarget] = []
    if not targets:
        errors.append("targets: at least one target school is required")
    for i, raw in enumerate(targets):
        try:
            parsed.append(AdmissionTarget(**raw))
        except ValidationError as e:
            errors.extend(_format_validation(f"targets[{i}]", e))
    if errors or app is None:
        return {"error": "invalid input", "details": errors}
    result = estimate_portfolio(app, parsed, data_dir=data_dir, samples=samples,
                                with_levers=with_levers)
    return result.model_dump(mode="json")


def estimate_admission_json(
    applicant_json: str,
    targets_json: str,
    data_dir: str | None = None,
    samples: int = DEFAULT_SAMPLES,
) -> str:
    """String-to-string wrapper for the Pyodide worker."""
    try:
        applicant = json.loads(applicant_json)
        targets = json.loads(targets_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"invalid JSON: {e}"})
    if isinstance(targets, dict):
        targets = [targets]
    return json.dumps(
        estimate_from_dicts(applicant, targets, data_dir=data_dir, samples=samples),
        ensure_ascii=False,
    )
