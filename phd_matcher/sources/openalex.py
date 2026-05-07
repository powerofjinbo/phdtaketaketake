"""OpenAlex source adapter (Sprint-3-c1).

OpenAlex is the cross-STEM choice for v1: free, no API key required,
covers physics / cs / biology / chemistry / mse / math, exposes author
search · recent works · coauthorship overlap · concepts (topic tags) ·
publication year · venue metadata · author count.

Two modes:
  - **Fixture** (default for tests / offline-safe runs): reads pre-baked
    JSON files from a fixture directory. Test invocations and the CLI's
    default mode use this.
  - **Live** (opt-in via `live=True`): real HTTPS calls to
    https://api.openalex.org. Use only when the agent / user explicitly
    asks for live enrichment. Adds a `mailto` parameter per the OpenAlex
    polite-pool guidance.

Both modes return `AuthorRecord` / `WorkRecord` from `sources.base`.

Fixture layout (under `<fixture_dir>/openalex/`):
  find_author/<sanitized_name>__<sanitized_institution>.json
  find_author/<sanitized_name>.json                          (no institution)
  recent_works/<author_id>.json
  coauthored/<author_id_a>__<author_id_b>.json

Author IDs in fixtures may use any string; the collector treats them as
opaque.
"""

from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

from phd_matcher.sources.base import AuthorRecord, SourceAdapter, WorkRecord

OPENALEX_BASE = "https://api.openalex.org"


class OpenAlexAdapter(SourceAdapter):
    """OpenAlex adapter with fixture-first design.

    Construction:
      - `OpenAlexAdapter(fixture_dir=<path>)` — fixture mode (offline,
        deterministic, used by tests and dry runs).
      - `OpenAlexAdapter(live=True, mailto=<email>)` — live HTTP mode.
      - `OpenAlexAdapter()` — neither: returns None for everything (the
        offline-safe default that keeps `collect_evidence.py` runnable
        even when no source is configured; useful for sanity-testing
        the orchestration path).
    """

    name = "openalex"

    def __init__(
        self,
        fixture_dir: Path | None = None,
        live: bool = False,
        mailto: str | None = None,
        timeout_seconds: float = 5.0,
    ) -> None:
        super().__init__()
        self.fixture_dir = fixture_dir
        self.live = live
        self.mailto = mailto
        self.timeout_seconds = timeout_seconds

    # ---- Public API (overrides base) -----------------------------------

    def find_author(
        self, name: str, institution: str | None = None,
    ) -> AuthorRecord | None:
        if self.fixture_dir is not None:
            return self._fixture_find_author(name, institution)
        if self.live:
            return self._live_find_author(name, institution)
        return None

    def recent_works(
        self,
        author_id: str,
        since_year: int | None = None,
        limit: int = 50,
    ) -> list[WorkRecord]:
        if self.fixture_dir is not None:
            return self._fixture_recent_works(author_id, since_year, limit)
        if self.live:
            return self._live_recent_works(author_id, since_year, limit)
        return []

    def coauthored_works(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None = None,
    ) -> list[WorkRecord]:
        if self.fixture_dir is not None:
            return self._fixture_coauthored(author_id_a, author_id_b, since_year)
        if self.live:
            return self._live_coauthored(author_id_a, author_id_b, since_year)
        return []

    # ---- Fixture-mode helpers ------------------------------------------

    @staticmethod
    def _sanitize(s: str) -> str:
        return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_")

    def _fixture_find_author(
        self, name: str, institution: str | None,
    ) -> AuthorRecord | None:
        assert self.fixture_dir is not None
        base = self.fixture_dir / "openalex" / "find_author"
        candidates: list[Path] = []
        if institution:
            candidates.append(
                base / f"{self._sanitize(name)}__{self._sanitize(institution)}.json"
            )
        candidates.append(base / f"{self._sanitize(name)}.json")
        for path in candidates:
            if path.exists():
                data = json.loads(path.read_text())
                return _author_from_fixture(data)
        self.errors.append(
            f"openalex fixture miss: find_author name={name!r} "
            f"institution={institution!r}"
        )
        return None

    def _fixture_recent_works(
        self, author_id: str, since_year: int | None, limit: int,
    ) -> list[WorkRecord]:
        assert self.fixture_dir is not None
        path = (
            self.fixture_dir / "openalex" / "recent_works"
            / f"{self._sanitize(author_id)}.json"
        )
        if not path.exists():
            self.errors.append(
                f"openalex fixture miss: recent_works author_id={author_id!r}"
            )
            return []
        data = json.loads(path.read_text())
        works = [_work_from_fixture(w) for w in data]
        if since_year is not None:
            works = [w for w in works if (w.year or 0) >= since_year]
        return works[:limit]

    def _fixture_coauthored(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None,
    ) -> list[WorkRecord]:
        assert self.fixture_dir is not None
        # Try both orderings — fixtures might be keyed either way.
        keys = [
            f"{self._sanitize(author_id_a)}__{self._sanitize(author_id_b)}",
            f"{self._sanitize(author_id_b)}__{self._sanitize(author_id_a)}",
        ]
        for key in keys:
            path = self.fixture_dir / "openalex" / "coauthored" / f"{key}.json"
            if path.exists():
                data = json.loads(path.read_text())
                works = [_work_from_fixture(w) for w in data]
                if since_year is not None:
                    works = [w for w in works if (w.year or 0) >= since_year]
                return works
        self.errors.append(
            f"openalex fixture miss: coauthored {author_id_a!r} × {author_id_b!r}"
        )
        return []

    # ---- Live-mode helpers ---------------------------------------------

    def _live_get(self, path: str, params: dict[str, str]) -> dict[str, Any] | None:
        if self.mailto:
            params = {**params, "mailto": self.mailto}
        url = f"{OPENALEX_BASE}{path}?{urllib.parse.urlencode(params)}"
        try:
            with urllib.request.urlopen(url, timeout=self.timeout_seconds) as resp:
                return json.loads(resp.read())
        except Exception as e:
            self.errors.append(f"openalex live error: {url} → {e}")
            return None

    def _live_find_author(
        self, name: str, institution: str | None,
    ) -> AuthorRecord | None:
        params = {"search": name, "per-page": "5"}
        if institution:
            params["filter"] = (
                f"last_known_institutions.display_name.search:{institution}"
            )
        data = self._live_get("/authors", params)
        if not data:
            return None
        results = data.get("results") or []
        if not results:
            return None
        a = results[0]
        return AuthorRecord(
            source="openalex",
            id=str(a.get("id", "")).removeprefix(f"{OPENALEX_BASE}/").lstrip("A"),
            name=a.get("display_name", name),
            institutions=[
                (inst.get("display_name") or "")
                for inst in (a.get("last_known_institutions") or [])
            ],
            profile_url=a.get("id", ""),
            h_index=(a.get("summary_stats") or {}).get("h_index"),
            works_count=a.get("works_count"),
            concepts=[
                (c.get("display_name") or "")
                for c in (a.get("x_concepts") or [])[:5]
            ],
        )

    def _live_recent_works(
        self, author_id: str, since_year: int | None, limit: int,
    ) -> list[WorkRecord]:
        # Author id may already include the "A" prefix; live filters use the openalex form.
        author_filter = author_id if author_id.startswith("A") else f"A{author_id}"
        params = {
            "filter": f"author.id:{author_filter}",
            "per-page": str(min(limit, 50)),
            "sort": "publication_year:desc",
        }
        if since_year is not None:
            params["filter"] += f",from_publication_date:{since_year}-01-01"
        data = self._live_get("/works", params)
        if not data:
            return []
        return [
            _work_from_openalex_live(w)
            for w in (data.get("results") or [])
        ]

    def _live_coauthored(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None,
    ) -> list[WorkRecord]:
        a = author_id_a if author_id_a.startswith("A") else f"A{author_id_a}"
        b = author_id_b if author_id_b.startswith("A") else f"A{author_id_b}"
        # OpenAlex supports comma-separated author.id filter values for
        # AND semantics (works that have BOTH authors).
        params = {
            "filter": f"author.id:{a},author.id:{b}",
            "per-page": "50",
            "sort": "publication_year:desc",
        }
        if since_year is not None:
            params["filter"] += f",from_publication_date:{since_year}-01-01"
        data = self._live_get("/works", params)
        if not data:
            return []
        return [
            _work_from_openalex_live(w)
            for w in (data.get("results") or [])
        ]


# ---- Record builders -----------------------------------------------------

def _author_from_fixture(data: dict[str, Any]) -> AuthorRecord:
    return AuthorRecord(
        source="openalex",
        id=str(data.get("id", "")),
        name=data.get("name", ""),
        institutions=list(data.get("institutions") or []),
        profile_url=data.get("profile_url", ""),
        h_index=data.get("h_index"),
        works_count=data.get("works_count"),
        concepts=list(data.get("concepts") or []),
    )


def _work_from_fixture(data: dict[str, Any]) -> WorkRecord:
    return WorkRecord(
        source="openalex",
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


def _work_from_openalex_live(w: dict[str, Any]) -> WorkRecord:
    """Map OpenAlex API JSON to WorkRecord."""
    authorships = w.get("authorships") or []
    return WorkRecord(
        source="openalex",
        id=str(w.get("id", "")),
        title=w.get("title") or w.get("display_name") or "",
        venue=(
            (w.get("primary_location") or {}).get("source") or {}
        ).get("display_name") or "",
        year=w.get("publication_year"),
        author_count=len(authorships) if authorships else None,
        author_ids=[
            str((au.get("author") or {}).get("id", ""))
            for au in authorships
        ],
        doi=w.get("doi"),
        url=w.get("id", ""),
        concepts=[
            (c.get("display_name") or "")
            for c in (w.get("concepts") or [])[:5]
        ],
    )
