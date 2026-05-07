"""DBLP source adapter (Sprint-3-c3).

Optimized for CS / theoretical CS. Live mode hits DBLP's open API.
Same fixture-first design — tests use disk fixtures.

Fixture layout: `<fixture_dir>/dblp/{find_author,recent_works,
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

DBLP_BASE = "https://dblp.org"


class DBLPAdapter(SourceAdapter):
    """DBLP adapter for CS-heavy fields."""

    name = "dblp"

    def __init__(
        self,
        fixture_dir: Path | None = None,
        live: bool = False,
        timeout_seconds: float = 5.0,
    ) -> None:
        super().__init__()
        self.fixture = (
            FixtureLookup(self.name, fixture_dir) if fixture_dir else None
        )
        self.live = live
        self.timeout_seconds = timeout_seconds

    def find_author(
        self, name: str, institution: str | None = None,
    ) -> AuthorRecord | None:
        if self.fixture is not None:
            p = self.fixture.find_author_path(name, institution)
            if p is None:
                self.errors.append(
                    f"dblp fixture miss: find_author name={name!r} "
                    f"institution={institution!r}"
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
                    f"dblp fixture miss: recent_works author_id={author_id!r}"
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
                    f"dblp fixture miss: coauthored "
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
        params = {**params, "format": "json"}
        url = f"{DBLP_BASE}{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read())
        except Exception as e:
            self.errors.append(f"dblp live error: {url} → {e}")
            return None

    def _live_find_author(
        self, name: str, institution: str | None,
    ) -> AuthorRecord | None:
        data = self._live_get("/search/author/api", {"q": name, "h": "5"})
        if not data:
            return None
        hits = (
            data.get("result", {}).get("hits", {}).get("hit") or []
        )
        if not hits:
            return None
        info = hits[0].get("info") or {}
        author_url = info.get("url", "")
        return AuthorRecord(
            source=self.name,
            id=author_url.split("/pid/")[-1] if "/pid/" in author_url else info.get("author", name),
            name=info.get("author", name),
            institutions=([institution] if institution else []),
            profile_url=author_url,
        )

    def _live_recent_works(
        self, author_id: str, since_year: int | None, limit: int,
    ) -> list[WorkRecord]:
        # DBLP author endpoint returns publications under /pid/<id>.xml
        # For v1 live mode, return empty and let users prefer fixtures.
        # (Full live impl needs XML parsing; deferred to c5.)
        self.errors.append(
            f"dblp live recent_works: not implemented in v1 "
            f"(author_id={author_id})"
        )
        return []

    def _live_coauthored(
        self, author_id_a: str, author_id_b: str, since_year: int | None,
    ) -> list[WorkRecord]:
        # Same — DBLP coauthored requires walking each author's
        # publications and intersecting. Deferred to c5.
        self.errors.append(
            "dblp live coauthored_works: not implemented in v1"
        )
        return []
