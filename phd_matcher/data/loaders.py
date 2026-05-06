"""Load journal tier YAML files (used as authoritative tier reference)."""

from __future__ import annotations

from pathlib import Path
from typing import Union

import yaml


def load_journal_tiers(data_dir: Union[str, Path], field: str) -> dict:
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
