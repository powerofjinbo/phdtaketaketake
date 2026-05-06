"""Load advisor cache, journal tier YAML, and school ranking YAML."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Union

import yaml

from phd_matcher.models import CandidateAdvisor


def load_advisors(data_dir: Union[str, Path], field: str) -> list[CandidateAdvisor]:
    """Load candidate advisors for a given field.

    Tries `<data_dir>/advisors/<field>_cache.json` first (real cache from OpenAlex);
    falls back to `<data_dir>/advisors/mock_advisors.json` (bundled mock data).
    """
    data_dir = Path(data_dir)
    cache_path = data_dir / "advisors" / f"{field}_cache.json"
    mock_path = data_dir / "advisors" / "mock_advisors.json"

    path = cache_path if cache_path.exists() else mock_path
    if not path.exists():
        return []

    with open(path) as f:
        records = json.load(f)

    return [CandidateAdvisor(**r) for r in records if r.get("field") == field]


def load_journal_tiers(data_dir: Union[str, Path], field: str) -> dict:
    """Load journal tier YAML for a field."""
    data_dir = Path(data_dir)
    yaml_path = data_dir / "journals" / f"{field}.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"Journal tier YAML not found: {yaml_path}")
    with open(yaml_path) as f:
        return yaml.safe_load(f)


def load_schools(data_dir: Union[str, Path]) -> dict:
    """Load US News PhD program ranking by field."""
    data_dir = Path(data_dir)
    yaml_path = data_dir / "schools" / "us_news_rank.yaml"
    with open(yaml_path) as f:
        return yaml.safe_load(f)
