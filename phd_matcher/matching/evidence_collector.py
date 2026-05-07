"""Evidence collector (Sprint-3-c1).

Drives a `SourceAdapter` to enrich `CandidateAdvisor` records with
evidence and raw facts — research areas, recent papers, connection-edge
counts (small_team / big_collab), most_recent_connection_year, etc.

Invariants:
  - Source adapters produce **evidence + raw facts only**. The collector
    never invents scores; the matcher's deterministic scoring stays in
    `phd_matcher.scoring.*`. Pinned by
    `test_collect_evidence_does_not_modify_scores`.
  - Already-filled fields are NOT overwritten — the agent's manual JSON
    wins. The collector only fills when the field is absent / default.
  - Verified-empty paths use `supports_fields=["path:<id>"]` per the
    existing strict-mode contract.
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass, field
from typing import Any

from phd_matcher.models import (
    CandidateAdvisor,
    CurrentAdvisor,
    EvidenceEntry,
    EvidenceSource,
    FieldProfile,
    PathEdge,
    StudentProfile,
)
from phd_matcher.sources.base import SourceAdapter, WorkRecord

DEFAULT_BIG_COLLAB_THRESHOLD = 10
DEFAULT_RECENT_WINDOW_YEARS = 5


@dataclass
class CollectionEntry:
    candidate_id: str
    field: str
    status: str    # "filled" / "unresolved"
    detail: str = ""


@dataclass
class CollectionResult:
    """Per-run summary returned by `EvidenceCollector.summary()`."""

    fields_attempted: int = 0
    fields_filled: int = 0
    fields_unresolved: int = 0
    source_errors: list[str] = field(default_factory=list)
    unresolved_repair_queue: list[dict] = field(default_factory=list)
    filled_log: list[dict] = field(default_factory=list)


class EvidenceCollector:
    """Walk each candidate × each field, attempt to fill via the adapter,
    and track which attempts succeeded / failed.

    Usage:
        collector = EvidenceCollector(adapter, current_year=2026,
                                       field_profile=physics)
        for cand in candidates:
            collector.collect_for_candidate(student, cand)
        summary = collector.summary()
    """

    def __init__(
        self,
        adapter: SourceAdapter,
        *,
        current_year: int | None = None,
        field_profile: FieldProfile | None = None,
        recent_window_years: int = DEFAULT_RECENT_WINDOW_YEARS,
    ) -> None:
        self.adapter = adapter
        self.current_year = current_year or datetime.datetime.now().year
        self.field_profile = field_profile
        self.recent_window_years = recent_window_years
        self._entries: list[CollectionEntry] = []

    # ---- Per-candidate orchestration -----------------------------------

    def collect_for_candidate(
        self, student: StudentProfile, candidate: CandidateAdvisor,
    ) -> CandidateAdvisor:
        """Mutate the candidate in-place with newly-fetched evidence.

        Order:
          1. Find the candidate's author record.
          2. Fill `research_areas` from concepts (when empty).
          3. Fill `paths_to_advisors[<adv.id>]` from coauthored works
             (per advisor; when not already set).
          4. (recent_papers / contribution / etc. deferred to later
             sprints — Sprint-3-c1 focuses on the highest-leverage edges.)
        """
        cand_author = self.adapter.find_author(
            candidate.name, candidate.institution,
        )
        if cand_author is None:
            self._record_unresolved(
                candidate.id, "author_lookup",
                f"adapter={self.adapter.name} could not find {candidate.name!r} "
                f"at {candidate.institution!r}",
            )
            return candidate

        self._fill_research_areas(candidate, cand_author)

        # Per-advisor path enrichment
        for advisor in student.current_advisors:
            self._fill_path_to_advisor(
                candidate, cand_author.id, advisor,
            )

        return candidate

    # ---- Field-specific fillers ---------------------------------------

    def _fill_research_areas(
        self, candidate: CandidateAdvisor, cand_author,
    ) -> None:
        self._entries.append(CollectionEntry(
            candidate_id=candidate.id, field="research_areas",
            status="attempted",
        ))
        if candidate.research_areas:
            # Already set — do not overwrite.
            self._record_filled(
                candidate.id, "research_areas",
                "skipped: already set by agent",
            )
            return

        concepts = list(cand_author.concepts) if cand_author.concepts else []
        if not concepts:
            # Try recent_works as a fallback for concepts
            since = self.current_year - 3
            works = self.adapter.recent_works(
                cand_author.id, since_year=since, limit=10,
            )
            concepts = self._aggregate_concepts(works, top_k=5)

        if not concepts:
            self._record_unresolved(
                candidate.id, "research_areas",
                "no concepts available from adapter",
            )
            return

        candidate.research_areas = concepts[:5]
        candidate.evidence["research_areas"] = EvidenceEntry(items=[
            EvidenceSource(
                url=cand_author.profile_url or "",
                source_type="openalex" if self.adapter.name == "openalex" else "other",
                claim=(
                    f"top concepts from {self.adapter.name}: "
                    f"{', '.join(concepts[:5])}"
                ),
                supports_fields=["research_areas"],
            ),
        ])
        self._record_filled(
            candidate.id, "research_areas",
            f"set from {self.adapter.name} concepts",
        )

    def _fill_path_to_advisor(
        self,
        candidate: CandidateAdvisor,
        cand_author_id: str,
        advisor: CurrentAdvisor,
    ) -> None:
        signal_name = f"path:{advisor.id}"
        self._entries.append(CollectionEntry(
            candidate_id=candidate.id, field=signal_name, status="attempted",
        ))

        # Skip if the agent already populated meaningful path data.
        existing = candidate.paths_to_advisors.get(advisor.id)
        if existing is not None and existing.has_any_edge:
            self._record_filled(
                candidate.id, signal_name,
                "skipped: agent already populated this path",
            )
            return

        adv_author = self.adapter.find_author(advisor.name, advisor.institution)
        if adv_author is None:
            self._record_unresolved(
                candidate.id, signal_name,
                f"adapter={self.adapter.name} could not find advisor "
                f"{advisor.name!r} at {advisor.institution!r}",
            )
            return

        since = self.current_year - self.recent_window_years
        works = self.adapter.coauthored_works(
            cand_author_id, adv_author.id, since_year=since,
        )

        threshold = (
            self.field_profile.big_collab_threshold
            if self.field_profile is not None
            else DEFAULT_BIG_COLLAB_THRESHOLD
        )

        if not works:
            # Verified-empty path: record the search itself with
            # supports_fields=["path:<id>"] per strict-mode contract.
            candidate.paths_to_advisors[advisor.id] = PathEdge(
                items=[EvidenceSource(
                    url="",
                    source_type=(
                        "openalex" if self.adapter.name == "openalex"
                        else "other"
                    ),
                    claim=(
                        f"searched {self.adapter.name} {since}–{self.current_year}: "
                        f"0 coauthored works between {advisor.name} and "
                        f"{candidate.name}"
                    ),
                    supports_fields=[signal_name],
                )],
                note=f"verified-empty via {self.adapter.name}",
            )
            self._record_filled(
                candidate.id, signal_name,
                "verified-empty (0 coauthored works)",
            )
            return

        small = [w for w in works if (w.author_count or 0) and (w.author_count or 0) <= threshold]
        big = [w for w in works if (w.author_count or 0) > threshold]
        years = [w.year for w in works if w.year is not None]
        most_recent = max(years) if years else None

        items: list[EvidenceSource] = [EvidenceSource(
            url=adv_author.profile_url or "",
            source_type=(
                "openalex" if self.adapter.name == "openalex" else "other"
            ),
            claim=(
                f"{len(small)} small-team (≤{threshold} authors) + "
                f"{len(big)} big-collab (>{threshold} authors) "
                f"coauthored works in {since}–{self.current_year}"
            ),
            supports_fields=[
                "small_team_coauthor_5y",
                "big_collab_papers_5y",
            ],
        )]

        candidate.paths_to_advisors[advisor.id] = PathEdge(
            small_team_coauthor_5y=len(small) if small else None,
            big_collab_papers_5y=len(big) if big else None,
            most_recent_connection_year=most_recent,
            items=items,
            note=f"enriched via {self.adapter.name}",
        )
        self._record_filled(
            candidate.id, signal_name,
            f"{len(small)} small-team + {len(big)} big-collab works "
            f"(most recent: {most_recent})",
        )

    # ---- Concept aggregation ------------------------------------------

    @staticmethod
    def _aggregate_concepts(
        works: list[WorkRecord], top_k: int = 5,
    ) -> list[str]:
        from collections import Counter
        c: Counter[str] = Counter()
        for w in works:
            for concept in w.concepts:
                if concept:
                    c[concept] += 1
        return [name for name, _ in c.most_common(top_k)]

    # ---- Tracking helpers ---------------------------------------------

    def _record_filled(
        self, candidate_id: str, field_name: str, detail: str,
    ) -> None:
        self._entries.append(CollectionEntry(
            candidate_id=candidate_id, field=field_name,
            status="filled", detail=detail,
        ))

    def _record_unresolved(
        self, candidate_id: str, field_name: str, detail: str,
    ) -> None:
        self._entries.append(CollectionEntry(
            candidate_id=candidate_id, field=field_name,
            status="unresolved", detail=detail,
        ))

    # ---- Summary -------------------------------------------------------

    def summary(self) -> dict:
        attempted = [e for e in self._entries if e.status == "attempted"]
        filled = [e for e in self._entries if e.status == "filled"]
        unresolved = [e for e in self._entries if e.status == "unresolved"]
        return {
            "fields_attempted": len(attempted),
            "fields_filled": len(filled),
            "fields_unresolved": len(unresolved),
            "source_errors": list(self.adapter.errors),
            "unresolved_repair_queue": [
                {
                    "candidate_id": e.candidate_id,
                    "signal": e.field,
                    "detail": e.detail,
                }
                for e in unresolved
            ],
            "filled_log": [
                {
                    "candidate_id": e.candidate_id,
                    "signal": e.field,
                    "detail": e.detail,
                }
                for e in filled
            ],
        }


def _candidate_to_dump(candidate: CandidateAdvisor) -> dict[str, Any]:
    """Helper to serialize an enriched candidate back to JSON-friendly dict."""
    return candidate.model_dump(mode="json", exclude_none=False)
