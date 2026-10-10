#!/usr/bin/env python3
"""Estimate the probability of an offer from one or more target programs.

    phdtaketaketake-admission \\
        --applicant-file applicant.json \\
        --targets-file targets.json

`applicant.json` is an AdmissionApplicant (GPA, transcript, publications,
research interests and application direction are required; GRE optional).
`targets.json` is one AdmissionTarget or a list of them — a school plus,
optionally, a professor researched exactly like a matcher candidate.

Refit the model against real outcomes:

    phdtaketaketake-admission --calibrate outcomes.json

Output: JSON to stdout. Errors: {"error": ..., "details": [...]}, exit 2.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

from phd_matcher.admission.api import estimate_from_dicts
from phd_matcher.admission.calibrate import Outcome, calibrate
from phd_matcher.admission.estimator import DEFAULT_SAMPLES

_DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Estimate P(offer) for target programs / professors (phdtaketaketake)."
    )
    ap.add_argument("--applicant-file", type=Path, help="AdmissionApplicant JSON")
    ap.add_argument("--targets-file", type=Path, help="AdmissionTarget JSON (object or list)")
    ap.add_argument("--calibrate", type=Path, metavar="OUTCOMES",
                    help="Fit the calibration block from a JSON list of outcomes")
    ap.add_argument("--samples", type=int, default=DEFAULT_SAMPLES)
    ap.add_argument("--no-levers", action="store_true", help="Skip what-if levers (faster)")
    ap.add_argument("--data-dir", type=Path, default=_DEFAULT_DATA_DIR)
    args = ap.parse_args()

    if args.calibrate:
        try:
            outcomes = [Outcome(**o) for o in _read_json(args.calibrate)]
            result = calibrate(outcomes, data_dir=args.data_dir)
        except (ValidationError, ValueError, json.JSONDecodeError) as e:
            json.dump({"error": f"calibrate: {e}"}, sys.stdout, ensure_ascii=False)
            sys.stdout.write("\n")
            return 2
        json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
        sys.stdout.write("\n")
        return 0

    if not args.applicant_file or not args.targets_file:
        ap.error("--applicant-file and --targets-file are required (or use --calibrate)")
    try:
        applicant = _read_json(args.applicant_file)
        targets = _read_json(args.targets_file)
    except (OSError, json.JSONDecodeError) as e:
        json.dump({"error": f"input: {e}"}, sys.stdout)
        sys.stdout.write("\n")
        return 2
    if isinstance(targets, dict):
        targets = [targets]
    if args.samples < 200:
        ap.error("--samples must be at least 200")

    result = estimate_from_dicts(applicant, targets, data_dir=args.data_dir,
                                 samples=args.samples, with_levers=not args.no_levers)
    json.dump(result, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")
    return 2 if "error" in result else 0


if __name__ == "__main__":
    sys.exit(main())
