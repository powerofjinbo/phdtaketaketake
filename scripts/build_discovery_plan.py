#!/usr/bin/env python3
"""Thin shim — see phd_matcher/cli/build_discovery_plan.py for the actual implementation.

Allows running the CLI directly from a checkout via:
    python scripts/build_discovery_plan.py ...

After `pip install` the canonical entry point is the console script:
    phdtaketaketake-build-discovery-plan ...
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow running without install: prepend the repo root to sys.path so
# `phd_matcher` is importable from a fresh checkout.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from phd_matcher.cli.build_discovery_plan import main

if __name__ == "__main__":
    sys.exit(main())
