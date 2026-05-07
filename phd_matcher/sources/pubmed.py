"""PubMed source adapter (Sprint-3-c3).

Optimized for biology / biomedical fields. Live mode hits NCBI
E-utilities (free, no API key for low rate, with key for higher).
Same fixture-first design as OpenAlex — tests use disk fixtures.

Fixture layout: `<fixture_dir>/pubmed/{find_author,recent_works,
coauthored}/<key>.json` matching the shared `FixtureLookup` convention.

> **Live mode is opt-in.** Without `--live` and without a fixture
> directory, the adapter no-ops (offline-safe).
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from phd_matcher.sources.base import (
    AuthorRecord,
    FixtureLookup,
    SourceAdapter,
    WorkRecord,
)

PUBMED_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


class PubMedAdapter(SourceAdapter):
    """PubMed adapter. Live mode uses NCBI E-utilities (esearch + efetch)."""

    name = "pubmed"

    def __init__(
        self,
        fixture_dir: Path | None = None,
        live: bool = False,
        api_key: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        super().__init__()
        self.fixture = (
            FixtureLookup(self.name, fixture_dir) if fixture_dir else None
        )
        self.live = live
        self.api_key = api_key
        self.timeout_seconds = timeout_seconds

    # ---- Public API ----------------------------------------------------

    def find_author(
        self, name: str, institution: str | None = None,
    ) -> AuthorRecord | None:
        if self.fixture is not None:
            p = self.fixture.find_author_path(name, institution)
            if p is None:
                self.errors.append(
                    f"pubmed fixture miss: find_author name={name!r} "
                    f"institution={institution!r}"
                )
                return None
            return _author_from_dict(json.loads(p.read_text()), self.name)
        if self.live:
            return self._live_find_author(name, institution)
        return None

    def recent_works(
        self,
        author_id: str,
        since_year: int | None = None,
        limit: int = 50,
    ) -> list[WorkRecord]:
        if self.fixture is not None:
            p = self.fixture.recent_works_path(author_id)
            if p is None:
                self.errors.append(
                    f"pubmed fixture miss: recent_works author_id={author_id!r}"
                )
                return []
            data = json.loads(p.read_text())
            works = [_work_from_dict(w, self.name) for w in data]
            if since_year is not None:
                works = [w for w in works if (w.year or 0) >= since_year]
            return works[:limit]
        if self.live:
            return self._live_recent_works(author_id, since_year, limit)
        return []

    def coauthored_works(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None = None,
    ) -> list[WorkRecord]:
        if self.fixture is not None:
            p = self.fixture.coauthored_path(author_id_a, author_id_b)
            if p is None:
                self.errors.append(
                    f"pubmed fixture miss: coauthored "
                    f"{author_id_a!r} × {author_id_b!r}"
                )
                return []
            data = json.loads(p.read_text())
            works = [_work_from_dict(w, self.name) for w in data]
            if since_year is not None:
                works = [w for w in works if (w.year or 0) >= since_year]
            return works
        if self.live:
            return self._live_coauthored(author_id_a, author_id_b, since_year)
        return []

    # ---- Live-mode helpers ---------------------------------------------

    def _live_get_json(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        params = {**params, "retmode": "json"}
        if self.api_key:
            params["api_key"] = self.api_key
        url = f"{PUBMED_BASE}{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read())
        except Exception as e:
            self.errors.append(f"pubmed live error: {url} → {e}")
            return None

    def _live_find_author(
        self, name: str, institution: str | None,
    ) -> AuthorRecord | None:
        # PubMed doesn't expose a stable author identifier; we represent
        # the "author id" as the canonical name string used in subsequent
        # searches (e.g., `Wang L[au]`).
        # For v1 live mode we just return the name as id; recent_works
        # / coauthored will use it as a search term.
        term = f'"{name}"[au]'
        if institution:
            term += f' AND "{institution}"[ad]'
        data = self._live_get_json("/esearch.fcgi", {
            "db": "pubmed", "term": term, "retmax": "5",
        })
        if not data or not data.get("esearchresult", {}).get("idlist"):
            return None
        return AuthorRecord(
            source=self.name, id=name, name=name,
            institutions=[institution] if institution else [],
            profile_url=f"https://pubmed.ncbi.nlm.nih.gov/?term={urllib.parse.quote(term)}",
        )

    def _live_recent_works(
        self, author_id: str, since_year: int | None, limit: int,
    ) -> list[WorkRecord]:
        # author_id is the author name string (see _live_find_author)
        term = f'"{author_id}"[au]'
        if since_year is not None:
            term += f" AND {since_year}:3000[dp]"
        data = self._live_get_json("/esearch.fcgi", {
            "db": "pubmed", "term": term, "retmax": str(min(limit, 50)),
            "sort": "pub date",
        })
        if not data:
            return []
        ids = data.get("esearchresult", {}).get("idlist", [])
        # For v1 we don't fetch full metadata via efetch — leave fields
        # mostly empty and let the agent expand if needed. Future c4
        # / c5 can hit efetch for title + venue + author count.
        return [
            WorkRecord(source=self.name, id=str(pmid), url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
            for pmid in ids
        ]

    def _live_coauthored(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None,
    ) -> list[WorkRecord]:
        term = f'"{author_id_a}"[au] AND "{author_id_b}"[au]'
        if since_year is not None:
            term += f" AND {since_year}:3000[dp]"
        data = self._live_get_json("/esearch.fcgi", {
            "db": "pubmed", "term": term, "retmax": "50",
        })
        if not data:
            return []
        ids = data.get("esearchresult", {}).get("idlist", [])
        return [
            WorkRecord(source=self.name, id=str(pmid), url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/")
            for pmid in ids
        ]


def _author_from_dict(data: dict[str, Any], source: str) -> AuthorRecord:
    return AuthorRecord(
        source=source,
        id=str(data.get("id", "")),
        name=data.get("name", ""),
        institutions=list(data.get("institutions") or []),
        profile_url=data.get("profile_url", ""),
        h_index=data.get("h_index"),
        works_count=data.get("works_count"),
        concepts=list(data.get("concepts") or []),
    )


def _work_from_dict(data: dict[str, Any], source: str) -> WorkRecord:
    return WorkRecord(
        source=source,
        id=str(data.get("id", "")),
        title=data.get("title", ""),
        venue=data.get("venue", ""),
        year=data.get("year"),
        author_count=data.get("author_count"),
        author_ids=list(data.get("author_ids") or []),
        doi=data.get("doi"),
        url=data.get("url", ""),
        concepts=list(data.get("concepts") or []),
    )
