#!/usr/bin/env python3
"""Thin shim — see phd_matcher/cli/match.py for the actual implementation.

Allows running the CLI directly from a checkout via:
    python scripts/match.py ...

After `pip install` the canonical entry point is the console script:
    phdtaketaketake-match ...
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running without install: prepend the repo root to sys.path so
# `phd_matcher` is importable from a fresh checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phd_matcher.cli.match import main

if __name__ == "__main__":
    sys.exit(main())
