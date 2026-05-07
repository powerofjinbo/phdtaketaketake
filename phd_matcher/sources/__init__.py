"""Source adapters for evidence collection (Sprint-3-c1).

Adapter base + records live in `base.py`. Per-source adapters (OpenAlex
in v1, PubMed / DBLP / Semantic Scholar in later sprints) live in their
own modules. The `EvidenceCollector` in
`phd_matcher.matching.evidence_collector` orchestrates them.

Hard architectural rule: source adapters produce **evidence + raw facts
only**. They do NOT compute scores. Scoring stays deterministic in the
existing scoring/ modules. Pinned by
`test_collect_evidence_does_not_modify_scores`.
"""

from phd_matcher.sources.base import (
    AuthorRecord,
    SourceAdapter,
    WorkRecord,
)

__all__ = [
    "AuthorRecord",
    "SourceAdapter",
    "WorkRecord",
]
