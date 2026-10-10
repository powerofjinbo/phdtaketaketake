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


# Optional research blocks, dropped in this order when a target fails
# validation in lenient mode (LLM-researched data is often slightly off).
_DROPPABLE = ("stats", "program_profile", "pi")


def _parse_target(raw: dict, i: int, lenient: bool) -> tuple[AdmissionTarget | None, list[str],
                                                              list[str]]:
    """Return (target, errors, warnings)."""
    try:
        return AdmissionTarget(**raw), [], []
    except ValidationError as e:
        first_errors = _format_validation(f"targets[{i}]", e)
    if not lenient:
        return None, first_errors, []
    trimmed = dict(raw)
    dropped: list[str] = []
    for key in _DROPPABLE:
        if key not in trimmed:
            continue
        trimmed.pop(key)
        dropped.append(key)
        try:
            tgt = AdmissionTarget(**trimmed)
        except ValidationError:
            continue
        name = raw.get("institution") or raw.get("id") or f"target {i}"
        return tgt, [], [
            f"{name}: researched {', '.join(dropped)} did not validate and was left out "
            f"({first_errors[0] if first_errors else 'schema error'})"
        ]
    return None, first_errors, []


def estimate_from_dicts(
    applicant: dict,
    targets: list[dict],
    *,
    data_dir: str | Path | None = None,
    samples: int = DEFAULT_SAMPLES,
    with_levers: bool = True,
    lenient: bool = False,
) -> dict:
    """Validate and estimate. With `lenient=True`, a target whose
    researched blocks (stats → program_profile → pi) fail validation is
    retried without them, and the estimate carries a warning saying so —
    the applicant's own inputs are never relaxed."""
    errors: list[str] = []
    try:
        app = AdmissionApplicant(**applicant)
    except ValidationError as e:
        errors.extend(_format_validation("applicant", e))
        app = None
    parsed: list[AdmissionTarget] = []
    target_warnings: dict[str, list[str]] = {}
    if not targets:
        errors.append("targets: at least one target school is required")
    for i, raw in enumerate(targets):
        if not isinstance(raw, dict):
            errors.append(f"targets[{i}]: not a JSON object")
            continue
        tgt, errs, warns = _parse_target(raw, i, lenient)
        errors.extend(errs)
        if tgt is not None:
            parsed.append(tgt)
            target_warnings[tgt.id] = warns
    if errors or app is None:
        return {"error": "invalid input", "details": errors}
    try:
        result = estimate_portfolio(app, parsed, data_dir=data_dir, samples=samples,
                                    with_levers=with_levers)
    except ValueError as e:
        return {"error": str(e), "details": []}
    for est in result.estimates:
        est.warnings = [*target_warnings.get(est.target_id, []), *est.warnings]
    return result.model_dump(mode="json")


def estimate_admission_json(
    applicant_json: str,
    targets_json: str,
    data_dir: str | None = None,
    samples: int = DEFAULT_SAMPLES,
    lenient: bool = True,
) -> str:
    """String-to-string wrapper for the Pyodide worker (lenient by default:
    targets come from LLM research)."""
    try:
        applicant = json.loads(applicant_json)
        targets = json.loads(targets_json)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"invalid JSON: {e}"})
    if isinstance(targets, dict):
        targets = [targets]
    return json.dumps(
        estimate_from_dicts(applicant, targets, data_dir=data_dir, samples=samples,
                            lenient=lenient),
        ensure_ascii=False,
    )
