"""Loaders for project data: journal tier YAMLs + FieldProfile YAMLs."""

from __future__ import annotations

from pathlib import Path

import yaml

from phd_matcher.models import FieldProfile


def load_journal_tiers(data_dir: str | Path, field: str) -> dict:
    """Load journal tier YAML for a field.

    The YAML is the project's authoritative opinion on what counts as tier 1
    vs 2 vs 3 within a field — distinct from the agent's general training
    knowledge, which may diverge.

    Bundled YAMLs: physics, mse. For other fields the agent uses its own
    knowledge (anchored on the cross-field guidance in
    `references/journal_tiers.md`).
    """
    data_dir = Path(data_dir)
    yaml_path = data_dir / "journals" / f"{field}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Journal tier YAML not found: {yaml_path}")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def load_field_profile(data_dir: str | Path, field: str) -> FieldProfile | None:
    """Load `FieldProfile` for a field.

    Lookup order:
      1. Direct `data/field_profiles/<field>.yaml`
      2. Alias match — scan all profiles, find one whose `aliases` list
         contains `field` (case-insensitive)

    Returns `None` if no profile matches. The matcher falls back to
    field-agnostic defaults in that case.
    """
    data_dir = Path(data_dir)
    profiles_dir = data_dir / "field_profiles"

    if not profiles_dir.exists():
        return None

    direct = profiles_dir / f"{field}.yaml"
    if direct.exists():
        with open(direct) as f:
            return FieldProfile(**yaml.safe_load(f))

    needle = field.lower().strip()
    for path in sorted(profiles_dir.glob("*.yaml")):
        with open(path) as f:
            data = yaml.safe_load(f)
        if data.get("id", "").lower() == needle:
            return FieldProfile(**data)
        for alias in data.get("aliases", []) or []:
            if alias.lower() == needle:
                return FieldProfile(**data)

    return None
