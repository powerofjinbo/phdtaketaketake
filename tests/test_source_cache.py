"""Tests for CachedAdapter + RateLimitedAdapter (Sprint-3-c4)."""

from __future__ import annotations

import time
from pathlib import Path

from phd_matcher.sources import CachedAdapter, OpenAlexAdapter, RateLimitedAdapter
from phd_matcher.sources.base import AuthorRecord, SourceAdapter, WorkRecord

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURES = REPO_ROOT / "tests" / "fixtures"


# ---- Counting adapter for instrumented tests ----------------------------

class _CountingAdapter(SourceAdapter):
    """Test double: returns scripted results and counts inner calls."""
    name = "counting"

    def __init__(self) -> None:
        super().__init__()
        self.find_author_calls = 0
        self.recent_works_calls = 0
        self.coauthored_calls = 0
        self.scripted_author = AuthorRecord(
            source="counting", id="A_X", name="Counted",
            h_index=42, profile_url="https://example/A_X",
        )
        self.scripted_works = [
            WorkRecord(source="counting", id="W1", title="t1",
                       year=2024, author_count=4),
        ]

    def find_author(self, name, institution=None):
        self.find_author_calls += 1
        return self.scripted_author

    def recent_works(self, author_id, since_year=None, limit=50):
        self.recent_works_calls += 1
        return list(self.scripted_works)

    def coauthored_works(self, author_id_a, author_id_b, since_year=None):
        self.coauthored_calls += 1
        return list(self.scripted_works)


# ---- CachedAdapter -------------------------------------------------------

def test_cached_adapter_hits_inner_once_then_cache(tmp_path):
    inner = _CountingAdapter()
    cached = CachedAdapter(inner, cache_dir=tmp_path)

    a1 = cached.find_author("Prof. X", "MIT")
    a2 = cached.find_author("Prof. X", "MIT")    # cache hit

    assert inner.find_author_calls == 1, "inner should be called once"
    assert cached.cache_hits == 1
    assert cached.cache_writes == 1
    # Cached result should equal the original
    assert a1 == a2
    assert a1 is not None
    assert a1.id == "A_X"


def test_cached_adapter_keys_by_args(tmp_path):
    """Different (name, institution) pairs use different cache keys."""
    inner = _CountingAdapter()
    cached = CachedAdapter(inner, cache_dir=tmp_path)

    cached.find_author("Prof. X", "MIT")
    cached.find_author("Prof. X", "Stanford")    # different cache key
    cached.find_author("Prof. Y", "MIT")          # different cache key

    assert inner.find_author_calls == 3
    assert cached.cache_hits == 0


def test_cached_adapter_recent_works_caches(tmp_path):
    inner = _CountingAdapter()
    cached = CachedAdapter(inner, cache_dir=tmp_path)

    w1 = cached.recent_works("A_X", since_year=2020)
    w2 = cached.recent_works("A_X", since_year=2020)

    assert inner.recent_works_calls == 1
    assert cached.cache_hits == 1
    assert w1 == w2
    assert len(w1) == 1


def test_cached_adapter_coauthored_caches(tmp_path):
    inner = _CountingAdapter()
    cached = CachedAdapter(inner, cache_dir=tmp_path)

    cached.coauthored_works("A_X", "A_Y", since_year=2020)
    cached.coauthored_works("A_X", "A_Y", since_year=2020)

    assert inner.coauthored_calls == 1
    assert cached.cache_hits == 1


def test_cached_adapter_ttl_expires(tmp_path):
    """Setting ttl_seconds=0 means every call misses (cache always stale)."""
    inner = _CountingAdapter()
    cached = CachedAdapter(inner, cache_dir=tmp_path, ttl_seconds=0)

    cached.find_author("Prof. X", "MIT")
    # Force the cache file's mtime into the past
    cache_files = list(tmp_path.rglob("*.json"))
    assert cache_files
    old = time.time() - 100
    for p in cache_files:
        import os
        os.utime(p, (old, old))

    cached.find_author("Prof. X", "MIT")
    assert inner.find_author_calls == 2, "TTL-expired cache should re-call inner"


def test_cached_adapter_caches_none_results(tmp_path):
    """Caching None / empty results prevents repeated lookup misses
    (which would otherwise hit live API on every retry)."""
    class NeverFindsAdapter(SourceAdapter):
        name = "nf"

        def __init__(self):
            super().__init__()
            self.find_author_calls = 0

        def find_author(self, name, institution=None):
            self.find_author_calls += 1
            return None

    inner = NeverFindsAdapter()
    cached = CachedAdapter(inner, cache_dir=tmp_path)

    assert cached.find_author("Nobody", "Nowhere") is None
    assert cached.find_author("Nobody", "Nowhere") is None    # cache hit
    assert inner.find_author_calls == 1


def test_cached_adapter_preserves_inner_name_and_errors(tmp_path):
    """`name` follows the inner so the fixture/cache layout stays
    aligned. `errors` is a property forwarding to inner.errors."""
    inner = OpenAlexAdapter()
    cached = CachedAdapter(inner, cache_dir=tmp_path)
    assert cached.name == "openalex"

    # Append to inner.errors and confirm cached.errors reflects it
    inner.errors.append("test-error")
    assert "test-error" in cached.errors


# ---- RateLimitedAdapter --------------------------------------------------

def test_rate_limited_adapter_waits_between_calls():
    inner = _CountingAdapter()
    rl = RateLimitedAdapter(inner, min_interval_seconds=0.05)

    t0 = time.monotonic()
    rl.find_author("X", "Y")
    rl.find_author("X", "Y")    # forces ≥0.05s wait
    rl.find_author("X", "Y")
    elapsed = time.monotonic() - t0

    # Three calls + two waits → at least 0.10s total. Allow some slack.
    assert elapsed >= 0.10
    assert rl.waits >= 2
    assert inner.find_author_calls == 3


def test_rate_limited_adapter_first_call_no_wait():
    inner = _CountingAdapter()
    rl = RateLimitedAdapter(inner, min_interval_seconds=0.05)
    t0 = time.monotonic()
    rl.find_author("X", "Y")
    elapsed = time.monotonic() - t0
    # First call shouldn't sleep — no prior call timestamp.
    assert elapsed < 0.04
    assert rl.waits == 0


def test_rate_limited_adapter_passes_through_results():
    inner = _CountingAdapter()
    rl = RateLimitedAdapter(inner, min_interval_seconds=0.001)
    rec = rl.find_author("X", "Y")
    assert rec is not None
    assert rec.id == "A_X"
    works = rl.recent_works("A_X")
    assert len(works) == 1


def test_rate_limited_preserves_inner_errors_and_name():
    inner = _CountingAdapter()
    rl = RateLimitedAdapter(inner, min_interval_seconds=0.001)
    inner.errors.append("inner-error")
    assert rl.name == inner.name
    assert "inner-error" in rl.errors


# ---- Composition: cache wrapping rate-limit -----------------------------

def test_cache_and_rate_limit_compose(tmp_path):
    """Stacking: cache hits avoid the rate-limit wait entirely (since
    no inner call is made), making repeated portfolio re-runs fast."""
    inner = _CountingAdapter()
    rl = RateLimitedAdapter(inner, min_interval_seconds=0.10)
    cached = CachedAdapter(rl, cache_dir=tmp_path)

    # First call hits inner (records the timestamp)
    cached.find_author("X", "Y")
    # Second call is a cache hit — should NOT wait through the
    # rate-limit interval
    t0 = time.monotonic()
    cached.find_author("X", "Y")
    elapsed = time.monotonic() - t0
    assert elapsed < 0.05, f"cache hit should be fast, got {elapsed}s"
    assert inner.find_author_calls == 1
    assert cached.cache_hits == 1
