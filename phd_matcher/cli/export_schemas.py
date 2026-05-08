"""Export Pydantic models as JSON Schema files (Sprint-4-c3).

Lets other agents / front-end forms / CLI users construct valid JSON
without reading the Pydantic source. Generates one file per top-level
model under `schemas/<ModelName>.schema.json` (each is a complete,
self-contained JSON Schema with embedded `$defs` for nested types).

Usage:

    phdtaketaketake-export-schemas --out schemas/
    # or:
    python scripts/export_schemas.py --out schemas/

The output directory is overwritten — schemas are derived from the
Pydantic source of truth (`phd_matcher.models`), so re-running is the
canonical way to keep them current.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from pydantic import BaseModel

from phd_matcher.models import (
    CandidateAdvisor,
    EvidenceEntry,
    EvidenceSource,
    FieldProfile,
    MatchResult,
    OpportunitySignal,
    PathEdge,
    ProgramProfile,
    ResearchFit,
    StrategyRecommendation,
    StrategySummary,
    StudentProfile,
)

# Models to export. Each is a top-level surface that an agent or
# front-end form might need to construct. Nested types (e.g.
# AuthorRole, GenealogyRelation) appear as $defs in the parent schemas.
EXPORTED_MODELS: tuple[type[BaseModel], ...] = (
    StudentProfile,
    CandidateAdvisor,
    FieldProfile,
    PathEdge,
    EvidenceSource,
    EvidenceEntry,
    ResearchFit,
    OpportunitySignal,
    ProgramProfile,
    MatchResult,
    StrategyRecommendation,
    StrategySummary,
)


def export_schemas(out_dir: Path) -> list[Path]:
    """Write one JSON Schema file per exported model. Returns the list
    of written paths in deterministic order."""
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for model in EXPORTED_MODELS:
        schema = model.model_json_schema()
        path = out_dir / f"{model.__name__}.schema.json"
        path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n")
        written.append(path)
    return written


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Export Pydantic models from phd_matcher.models as JSON "
            "Schema files. Useful for downstream agents, front-end "
            "forms, or independent validators."
        ),
    )
    ap.add_argument(
        "--out", type=Path, required=True,
        help="Output directory (will be created; existing files overwritten)",
    )
    ap.add_argument(
        "--list", action="store_true",
        help="Print model names instead of writing files",
    )
    args = ap.parse_args()

    if args.list:
        for m in EXPORTED_MODELS:
            print(m.__name__)
        return 0

    written = export_schemas(args.out)
    for p in written:
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
