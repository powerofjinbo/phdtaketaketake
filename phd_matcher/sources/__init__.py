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
    FixtureLookup,
    SourceAdapter,
    WorkRecord,
)
from phd_matcher.sources.dblp import DBLPAdapter
from phd_matcher.sources.openalex import OpenAlexAdapter
from phd_matcher.sources.pubmed import PubMedAdapter
from phd_matcher.sources.semantic_scholar import SemanticScholarAdapter

# Per-field default adapter when --source is not explicitly given.
# Heuristic: pick the strongest single adapter for the field. Multi-
# adapter aggregation is deferred (Sprint-3-c4+).
DEFAULT_ADAPTER_BY_FIELD: dict[str, str] = {
    "physics":   "openalex",   # cross-STEM coverage; INSPIRE deferred
    "mse":       "openalex",
    "cs":        "semantic_scholar",
    "biology":   "pubmed",
    "chemistry": "openalex",
    "math":      "semantic_scholar",  # arXiv proper deferred
}

ADAPTER_CLASSES: dict[str, type[SourceAdapter]] = {
    "openalex": OpenAlexAdapter,
    "pubmed": PubMedAdapter,
    "dblp": DBLPAdapter,
    "semantic_scholar": SemanticScholarAdapter,
}


def select_adapter(
    name: str,
    *,
    fixture_dir=None,
    live: bool = False,
    mailto: str | None = None,
    api_key: str | None = None,
) -> SourceAdapter:
    """Construct an adapter by name with the given mode flags.

    Each adapter's constructor accepts a slightly different kwarg set
    (`mailto` for OpenAlex polite pool, `api_key` for PubMed /
    Semantic Scholar). Unknown kwargs are silently dropped.
    """
    if name not in ADAPTER_CLASSES:
        raise ValueError(
            f"unknown source adapter {name!r}; "
            f"valid: {sorted(ADAPTER_CLASSES)}"
        )
    cls = ADAPTER_CLASSES[name]
    kwargs: dict = {"fixture_dir": fixture_dir, "live": live}
    if name == "openalex":
        kwargs["mailto"] = mailto
    if name in ("pubmed", "semantic_scholar"):
        kwargs["api_key"] = api_key
    return cls(**kwargs)


def default_adapter_for_field(field_id: str | None) -> str:
    """Return the adapter name suitable for a given field. Falls back
    to OpenAlex when the field is unknown."""
    if field_id is None:
        return "openalex"
    return DEFAULT_ADAPTER_BY_FIELD.get(field_id, "openalex")


__all__ = [
    "ADAPTER_CLASSES",
    "AuthorRecord",
    "DBLPAdapter",
    "DEFAULT_ADAPTER_BY_FIELD",
    "FixtureLookup",
    "OpenAlexAdapter",
    "PubMedAdapter",
    "SemanticScholarAdapter",
    "SourceAdapter",
    "WorkRecord",
    "default_adapter_for_field",
    "select_adapter",
]
