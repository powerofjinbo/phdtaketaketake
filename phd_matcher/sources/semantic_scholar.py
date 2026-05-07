"""Semantic Scholar source adapter (Sprint-3-c3).

Cross-field, citation-graph aware. Live mode hits the Semantic Scholar
Graph API (free tier, optional API key for higher rate). Same fixture
layout.

Fixture layout: `<fixture_dir>/semantic_scholar/{find_author,recent_works,
coauthored}/<key>.json`.
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
from phd_matcher.sources.pubmed import _author_from_dict, _work_from_dict

S2_BASE = "https://api.semanticscholar.org/graph/v1"


class SemanticScholarAdapter(SourceAdapter):
    """Semantic Scholar adapter with citation-graph awareness."""

    name = "semantic_scholar"

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

    def find_author(
        self, name: str, institution: str | None = None,
    ) -> AuthorRecord | None:
        if self.fixture is not None:
            p = self.fixture.find_author_path(name, institution)
            if p is None:
                self.errors.append(
                    f"semantic_scholar fixture miss: find_author "
                    f"name={name!r} institution={institution!r}"
                )
                return None
            return _author_from_dict(json.loads(p.read_text()), self.name)
        if self.live:
            return self._live_find_author(name, institution)
        return None

    def recent_works(
        self, author_id: str, since_year: int | None = None, limit: int = 50,
    ) -> list[WorkRecord]:
        if self.fixture is not None:
            p = self.fixture.recent_works_path(author_id)
            if p is None:
                self.errors.append(
                    f"semantic_scholar fixture miss: recent_works "
                    f"author_id={author_id!r}"
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
        self, author_id_a: str, author_id_b: str, since_year: int | None = None,
    ) -> list[WorkRecord]:
        if self.fixture is not None:
            p = self.fixture.coauthored_path(author_id_a, author_id_b)
            if p is None:
                self.errors.append(
                    f"semantic_scholar fixture miss: coauthored "
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

    def _live_get(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        url = f"{S2_BASE}{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
        if self.api_key:
            req.add_header("x-api-key", self.api_key)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read())
        except Exception as e:
            self.errors.append(f"semantic_scholar live error: {url} → {e}")
            return None

    def _live_find_author(
        self, name: str, institution: str | None,
    ) -> AuthorRecord | None:
        data = self._live_get("/author/search", {
            "query": name, "limit": "5",
            "fields": "name,affiliations,hIndex,paperCount",
        })
        if not data:
            return None
        results = data.get("data") or []
        if not results:
            return None
        a = results[0]
        return AuthorRecord(
            source=self.name,
            id=str(a.get("authorId", "")),
            name=a.get("name", name),
            institutions=list(a.get("affiliations") or []),
            profile_url=f"https://www.semanticscholar.org/author/{a.get('authorId', '')}",
            h_index=a.get("hIndex"),
            works_count=a.get("paperCount"),
        )

    def _live_recent_works(
        self, author_id: str, since_year: int | None, limit: int,
    ) -> list[WorkRecord]:
        params = {
            "fields": "title,venue,year,authors,externalIds,fieldsOfStudy",
            "limit": str(min(limit, 50)),
        }
        data = self._live_get(f"/author/{author_id}/papers", params)
        if not data:
            return []
        results = data.get("data") or []
        works: list[WorkRecord] = []
        for w in results:
            year = w.get("year")
            if since_year is not None and (year or 0) < since_year:
                continue
            authors = w.get("authors") or []
            works.append(WorkRecord(
                source=self.name,
                id=str(w.get("paperId", "")),
                title=w.get("title", ""),
                venue=w.get("venue", ""),
                year=year,
                author_count=len(authors) if authors else None,
                author_ids=[str(au.get("authorId", "")) for au in authors],
                doi=(w.get("externalIds") or {}).get("DOI"),
                url=f"https://www.semanticscholar.org/paper/{w.get('paperId', '')}",
                concepts=list(w.get("fieldsOfStudy") or []),
            ))
        return works

    def _live_coauthored(
        self, author_id_a: str, author_id_b: str, since_year: int | None,
    ) -> list[WorkRecord]:
        # S2 doesn't have a direct "papers by both authors" endpoint;
        # walk one author's papers and filter by the other in author_ids.
        a_papers = self._live_recent_works(
            author_id_a, since_year=since_year, limit=200,
        )
        return [
            w for w in a_papers
            if author_id_b in w.author_ids
        ]
