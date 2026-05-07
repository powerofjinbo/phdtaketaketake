"""Source-adapter cache + rate-limit wrappers (Sprint-3-c4).

Two `SourceAdapter` decorators that compose with any inner adapter:

  - `CachedAdapter(inner, cache_dir, ttl_seconds=None)` — disk-cached
    JSON of every adapter call result. Optional TTL invalidates entries
    older than `ttl_seconds`. Cache hits avoid the inner call entirely.

  - `RateLimitedAdapter(inner, min_interval_seconds)` — sleeps before
    each inner call so consecutive calls are at least
    `min_interval_seconds` apart. Polite-pool friendly.

Composable: wrap one inside the other to get cache + rate-limit:

    inner = OpenAlexAdapter(live=True, mailto="me@example.edu")
    rl    = RateLimitedAdapter(inner, min_interval_seconds=0.1)
    cached = CachedAdapter(rl, cache_dir=Path("/tmp/openalex_cache"),
                           ttl_seconds=86400 * 7)

Both wrappers preserve the inner's `name` (so cached results land in
the right per-source fixture-style folder) and forward `errors` to the
inner so collector summaries still surface upstream failures.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

from phd_matcher.sources.base import (
    AuthorRecord,
    SourceAdapter,
    WorkRecord,
)


class CachedAdapter(SourceAdapter):
    """Disk-cached JSON wrapper for any SourceAdapter."""

    def __init__(
        self,
        inner: SourceAdapter,
        cache_dir: Path,
        *,
        ttl_seconds: int | None = None,
    ) -> None:
        # Intentionally do NOT call super().__init__() — that would
        # clobber `inner.errors` via our `errors` property setter
        # (we forward errors to the inner adapter so collector summaries
        # see upstream failures). All wrapper state lives below.
        self.inner = inner
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        # Preserve inner's name so the collector + fixture layout stay aligned.
        self.name = inner.name
        self.cache_hits = 0
        self.cache_writes = 0

    @property
    def errors(self) -> list[str]:  # type: ignore[override]
        return self.inner.errors

    @errors.setter
    def errors(self, value: list[str]) -> None:
        self.inner.errors = value

    def find_author(
        self, name: str, institution: str | None = None,
    ) -> AuthorRecord | None:
        key = self._cache_path("find_author", name, institution or "")
        cached = self._read_cache(key)
        if cached is not None:
            self.cache_hits += 1
            return None if not cached else AuthorRecord(**cached)
        result = self.inner.find_author(name, institution)
        self._write_cache(key, asdict(result) if result is not None else {})
        return result

    def recent_works(
        self,
        author_id: str,
        since_year: int | None = None,
        limit: int = 50,
    ) -> list[WorkRecord]:
        key = self._cache_path(
            "recent_works", author_id, since_year or "", limit,
        )
        cached = self._read_cache(key)
        if cached is not None:
            self.cache_hits += 1
            return [WorkRecord(**w) for w in cached]
        result = self.inner.recent_works(author_id, since_year, limit)
        self._write_cache(key, [asdict(w) for w in result])
        return result

    def coauthored_works(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None = None,
    ) -> list[WorkRecord]:
        key = self._cache_path(
            "coauthored", author_id_a, author_id_b, since_year or "",
        )
        cached = self._read_cache(key)
        if cached is not None:
            self.cache_hits += 1
            return [WorkRecord(**w) for w in cached]
        result = self.inner.coauthored_works(author_id_a, author_id_b, since_year)
        self._write_cache(key, [asdict(w) for w in result])
        return result

    # ---- Cache I/O -----------------------------------------------------

    def _cache_path(self, op: str, *parts: object) -> Path:
        key_str = f"{op}|" + "|".join(str(p) for p in parts)
        digest = hashlib.md5(key_str.encode("utf-8")).hexdigest()
        return self.cache_dir / self.name / op / f"{digest}.json"

    def _read_cache(self, path: Path) -> Any | None:
        if not path.exists():
            return None
        if self.ttl_seconds is not None:
            age = time.time() - path.stat().st_mtime
            if age > self.ttl_seconds:
                return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    def _write_cache(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            path.write_text(json.dumps(data))
            self.cache_writes += 1
        except OSError:
            # Cache writes are best-effort; failures don't break the call.
            pass


class RateLimitedAdapter(SourceAdapter):
    """Throttle inner adapter calls to at most one per `min_interval_seconds`.

    Designed for polite-pool API usage (OpenAlex 100ms / NCBI 100ms).
    Doesn't retry — combine with `CachedAdapter` for retry-via-cache.
    """

    def __init__(
        self,
        inner: SourceAdapter,
        min_interval_seconds: float = 0.1,
    ) -> None:
        # See CachedAdapter.__init__ for why we skip super().__init__().
        self.inner = inner
        self.min_interval = min_interval_seconds
        self.name = inner.name
        self._last_call_at: float = 0.0
        self.waits = 0
        self.total_wait_seconds = 0.0

    @property
    def errors(self) -> list[str]:  # type: ignore[override]
        return self.inner.errors

    @errors.setter
    def errors(self, value: list[str]) -> None:
        self.inner.errors = value

    def _wait(self) -> None:
        elapsed = time.monotonic() - self._last_call_at
        if elapsed < self.min_interval:
            sleep_for = self.min_interval - elapsed
            time.sleep(sleep_for)
            self.waits += 1
            self.total_wait_seconds += sleep_for
        self._last_call_at = time.monotonic()

    def find_author(
        self, name: str, institution: str | None = None,
    ) -> AuthorRecord | None:
        self._wait()
        return self.inner.find_author(name, institution)

    def recent_works(
        self,
        author_id: str,
        since_year: int | None = None,
        limit: int = 50,
    ) -> list[WorkRecord]:
        self._wait()
        return self.inner.recent_works(author_id, since_year, limit)

    def coauthored_works(
        self,
        author_id_a: str,
        author_id_b: str,
        since_year: int | None = None,
    ) -> list[WorkRecord]:
        self._wait()
        return self.inner.coauthored_works(author_id_a, author_id_b, since_year)
