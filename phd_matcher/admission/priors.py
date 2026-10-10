"""Load `data/admission/priors.yaml` and resolve per-field values.

Field lookup goes through `load_field_profile` so aliases ("hep",
"condensed matter", "machine learning"…) resolve to the same canonical id
the matcher uses. Unknown fields fall back to the `default` block.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from phd_matcher.data.loaders import load_field_profile

DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_FALLBACK_BASE_RATES = {"top_10": 0.10, "top_11_30": 0.15, "top_31_60": 0.22, "top_60_plus": 0.32}


@dataclass
class FieldPriors:
    field_id: str
    base_rates: dict[str, float]
    admission_model_prior: float
    subject_gre_weight: float
    core_course_keywords: list[str]
    pool_overrides: dict[str, dict[str, tuple[float, float]]] = field(default_factory=dict)


@dataclass
class Priors:
    intercept_shift: float
    beta_multiplier: float
    post_interview_rates: dict[str, float]
    waitlist_rates: dict[str, float]
    raw: dict

    def for_field(self, field_name: str, data_dir: Path) -> FieldPriors:
        fields = self.raw.get("fields", {}) or {}
        fid = field_name.lower().strip()
        if fid not in fields:
            profile = load_field_profile(data_dir, field_name)
            if profile is not None:
                fid = profile.id
        block = dict(self.raw.get("default", {}) or {})
        block.update(fields.get(fid, {}) or {})
        overrides = {
            feat: {tier: (float(v[0]), float(v[1])) for tier, v in tiers.items()}
            for feat, tiers in (block.get("pool_overrides") or {}).items()
        }
        return FieldPriors(
            field_id=fid if fid in fields else "default",
            base_rates={**_FALLBACK_BASE_RATES, **(block.get("base_rates") or {})},
            admission_model_prior=float(block.get("admission_model_prior", 0.5)),
            subject_gre_weight=float(block.get("subject_gre_weight", 0.03)),
            core_course_keywords=list(block.get("core_course_keywords") or []),
            pool_overrides=overrides,
        )


@lru_cache(maxsize=8)
def _load(path_str: str) -> Priors:
    path = Path(path_str)
    raw: dict = {}
    if path.exists():
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f) or {}
    cal = raw.get("calibration", {}) or {}
    return Priors(
        intercept_shift=float(cal.get("intercept_shift", 0.0)),
        beta_multiplier=float(cal.get("beta_multiplier", 1.0)),
        post_interview_rates={
            "top_10": 0.40, "top_11_30": 0.50, "top_31_60": 0.55, "top_60_plus": 0.60,
            **(raw.get("post_interview_rates") or {}),
        },
        waitlist_rates={
            "top_10": 0.20, "top_11_30": 0.25, "top_31_60": 0.30, "top_60_plus": 0.35,
            **(raw.get("waitlist_rates") or {}),
        },
        raw=raw,
    )


def load_priors(data_dir: str | Path | None = None) -> Priors:
    data_dir = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    return _load(str(data_dir / "admission" / "priors.yaml"))
