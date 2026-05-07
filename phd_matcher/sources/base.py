"""Source adapter base + record types (Sprint-3-c1).

Adapters fetch raw facts (author lookups, recent works, coauthored
works) from a real source — OpenAlex, PubMed, DBLP, Semantic Scholar.
Each adapter wraps either a live HTTP source or a fixture directory
(for offline-safe tests / dry runs).

> **Hard rule**: adapters produce evidence + raw facts only. They do
> NOT compute scores. The matcher's deterministic scoring stays in
> `phd_matcher.scoring.*`.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AuthorRecord:
    """Source-specific author lookup result."""

    source: str            # "openalex" / "semantic_scholar" / "pubmed" / etc.
    id: str                # source-specific identifier
    name: str
    institutions: list[str] = field(default_factory=list)
    profile_url: str = ""
    h_index: int | None = None
    works_count: int | None = None
    concepts: list[str] = field(default_factory=list)


@dataclass
class WorkRecord:
    """Source-specific publication / work record."""

    source: str
    id: str
    title: str = ""
    venue: str = ""
    year: int | None = None
    author_count: int | None = None
    author_ids: list[str] = field(default_factory=list)
    doi: str | None = None
    url: str = ""
    concepts: list[str] = field(default_factory=list)


class SourceAdapter:
    """Base class for source adapters. Subclasses override the four
    lookup methods. Default implementations return None / [] so a
    candidate can be partially enriched even when one adapter is
    unconfigured.

    Subclasses should track recoverable errors (HTTP failures, missing
    fixtures) on `self.errors` so the collector can surface them in
    `collection_summary.source_errors`.
    """

    name: str = "base"

    def __init__(self) -> None:
        self.errors: list[str] = []

    def find_author(
        self, name: str, institution: str | None = None,
    ) -> AuthorRecord | None:
        """Find an author by name (and optional institution disambiguator).
        Returns None when not found or when the adapter is unconfigured."""
        return None

    def recent_works(
        self,
        author_id: str,
        since_year: int | None = None,
        limit: int = 50,
    ) -> list[WorkRecord]:
        """Return recent works for the given source-specific author id."""
        return []

    def coauthored_works(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None = None,
    ) -> list[WorkRecord]:
        """Return works co-authored by both author ids in the given window."""
        return []
