"""Research-direction relevance.

v0.1 uses keyword overlap. Roadmap: swap in sentence-transformers / Voyage AI
embeddings without changing the call site.
"""

import re

# Tiny stopword list (english + a few common research filler words)
_STOPWORDS = {
    "the", "and", "for", "with", "via", "using", "study", "studies",
    "research", "physics", "science", "novel", "applications",
    "based", "approach", "method", "methods",
}


def _tokenize(text: str) -> set[str]:
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return {t for t in cleaned.split() if len(t) > 2 and t not in _STOPWORDS}


def direction_relevance(student_direction: str, advisor_areas: list[str]) -> float:
    """Jaccard-like overlap of keywords. Returns 0–1."""
    student_kws = _tokenize(student_direction)
    advisor_kws: set[str] = set()
    for area in advisor_areas:
        advisor_kws.update(_tokenize(area))

    if not student_kws or not advisor_kws:
        return 0.0

    overlap = student_kws & advisor_kws
    if not overlap:
        return 0.0

    return len(overlap) / len(student_kws | advisor_kws)


def filter_by_direction(candidates, student_direction: str, threshold: float = 0.0):
    """Filter candidates by minimum relevance. threshold=0 means no filtering."""
    if threshold <= 0:
        return list(candidates)
    return [
        c for c in candidates
        if direction_relevance(student_direction, c.research_areas) >= threshold
    ]
