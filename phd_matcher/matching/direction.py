"""Research-direction relevance.

Keyword overlap between the student's stated direction and the
candidate's research areas. Used as the last-resort research signal in
the sort key (behind the structured `research_fit` score).

v0.2 changes over the original Jaccard overlap:

- **Light stemming** — "networks"/"network", "learning"/"learned"/"learn"
  now match instead of counting as unrelated words.
- **CJK support** — Chinese / Japanese runs are split into character
  bigrams, so "量子计算" overlaps with "量子信息" on "量子" instead of the
  whole run being a single never-matching token.
- **Recall-weighted score (F2)** — Jaccard divides by the *union*, which
  punished PIs who list many research areas: a PI covering the student's
  whole direction plus four other topics scored below a PI covering half
  of it. F2 weights coverage of the student's direction 4× over the share
  of the PI's areas that match.

Roadmap: swap in embeddings without changing the call site.
"""

import re

# Tiny stopword list (english + a few common research filler words)
_STOPWORDS = {
    "the", "and", "for", "with", "via", "using", "study", "studies",
    "research", "physics", "science", "novel", "applications",
    "based", "approach", "method", "methods", "toward", "towards",
    "from", "into", "its", "their", "new",
}

_CJK_RUN = re.compile(r"[぀-ヿ㐀-䶿一-鿿]+")
_CJK_STOP_BIGRAMS = {"研究", "方向", "相关", "基于", "应用", "方法"}


def _stem(token: str) -> str:
    """Strip the most common English inflections. Deliberately minimal —
    it only has to make obvious variants collide, not be a real stemmer."""
    if len(token) > 4 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith("ing"):
        return token[:-3]
    if len(token) > 4 and token.endswith("ed") and not token.endswith("eed"):
        return token[:-2]
    if len(token) > 3 and token.endswith("s") and not token.endswith(("ss", "us", "is")):
        return token[:-1]
    return token


def _tokenize(text: str) -> set[str]:
    lowered = text.lower()
    tokens: set[str] = set()

    for run in _CJK_RUN.findall(lowered):
        if len(run) == 1:
            continue
        for i in range(len(run) - 1):
            bigram = run[i:i + 2]
            if bigram not in _CJK_STOP_BIGRAMS:
                tokens.add(bigram)

    latin = _CJK_RUN.sub(" ", lowered)
    cleaned = re.sub(r"[^\w\s]", " ", latin)
    for t in cleaned.split():
        if len(t) > 2 and t not in _STOPWORDS:
            tokens.add(_stem(t))
    return tokens


def direction_relevance(student_direction: str, advisor_areas: list[str]) -> float:
    """Recall-weighted keyword overlap (F2). Returns 0–1.

    recall    = |overlap| / |student keywords|
    precision = |overlap| / |advisor keywords|
    F2        = 5·P·R / (4·P + R)
    """
    student_kws = _tokenize(student_direction)
    advisor_kws: set[str] = set()
    for area in advisor_areas:
        advisor_kws.update(_tokenize(area))

    if not student_kws or not advisor_kws:
        return 0.0

    overlap = len(student_kws & advisor_kws)
    if overlap == 0:
        return 0.0

    recall = overlap / len(student_kws)
    precision = overlap / len(advisor_kws)
    return 5 * precision * recall / (4 * precision + recall)


def filter_by_direction(candidates, student_direction: str, threshold: float = 0.0):
    """Filter candidates by minimum relevance. threshold=0 means no filtering."""
    if threshold <= 0:
        return list(candidates)
    return [
        c for c in candidates
        if direction_relevance(student_direction, c.research_areas) >= threshold
    ]
