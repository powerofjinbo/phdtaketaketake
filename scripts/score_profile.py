#!/usr/bin/env python3
"""Score a profile dimensionally (P / G / E only) without candidate ranking.

The repo has no static candidate cache — connection scores are always
per-(student, candidate) pairs computed by the agent (see SKILL.md). This
script is for self-assessment of the publication / GPA / experience
dimensions in isolation, e.g. when the user just wants a sanity check on
their own profile before doing the full match flow.

Invocation mirrors match.py. Output: JSON {p_score, g_score, e_score, note}.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from phd_matcher.models import StudentProfile  # noqa: E402
from phd_matcher.scoring import experience, gpa, pub  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Compute the per-dimension scores of a profile (no candidate ranking). "
            "Field-agnostic: works for any STEM discipline."
        )
    )
    ap.add_argument("--profile-file", type=Path)
    ap.add_argument("--profile-json", type=str)
    args = ap.parse_args()

    if args.profile_file:
        profile_dict = json.loads(args.profile_file.read_text())
    elif args.profile_json:
        profile_dict = json.loads(args.profile_json)
    elif not sys.stdin.isatty():
        profile_dict = json.loads(sys.stdin.read())
    else:
        json.dump({"error": "no profile provided"}, sys.stdout)
        return 2

    student = StudentProfile(**profile_dict)

    p = pub.pub_score([pp.model_dump() for pp in student.papers])
    g = gpa.gpa_score(student.gpa_raw, student.gpa_scale)
    e = experience.experience_score([ee.model_dump() for ee in student.experiences])

    output = {
        "p_score": round(p, 2),
        "g_score": round(g, 2),
        "e_score": round(e, 2),
        "note": (
            "Connection (C) is computed per (student, candidate) pair, so it is "
            "omitted from this dimensional self-score. Run scripts/match.py to "
            "see Connection scores against bundled candidates."
        ),
    }
    json.dump(output, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
