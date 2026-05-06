"""phdtaketaketake — connection-first PhD advisor matcher (Claude Code skill)."""

from phd_matcher.matching.ranker import compute_match, rank_advisors

__version__ = "0.1.0"
__all__ = ["compute_match", "rank_advisors"]
