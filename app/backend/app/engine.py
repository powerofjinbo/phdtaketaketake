"""Bridge to the phd_matcher scoring engine (the phdtaketaketake skill)."""

import sys

from .config import DATA_DIR, SKILL_DIR

if str(SKILL_DIR) not in sys.path:
    sys.path.insert(0, str(SKILL_DIR))

from phd_matcher.data.loaders import load_field_profile  # noqa: E402
from phd_matcher.matching.ranker import rank_advisors, strict_validate  # noqa: E402
from phd_matcher.matching.strategy import (  # noqa: E402
    recommend_strategy,
    summarize_portfolio,
)
from phd_matcher.models import (  # noqa: E402
    CandidateAdvisor,
    StudentProfile,
)


def resolve_field_profile(field: str):
    return load_field_profile(DATA_DIR, field)


__all__ = [
    "CandidateAdvisor",
    "StudentProfile",
    "rank_advisors",
    "strict_validate",
    "recommend_strategy",
    "summarize_portfolio",
    "resolve_field_profile",
]
