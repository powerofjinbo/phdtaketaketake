# JSON Schemas

These files are the **JSON Schema (Draft 2020-12)** representation of
the Pydantic models in `phd_matcher.models`. They're useful for:

- **Other agents** that don't import the Python package — read these
  to know what JSON shape to produce when constructing a profile or
  candidate record.
- **Front-end forms / data-entry tools** — feed into form generators
  (e.g. JSON Forms, react-jsonschema-form) to render typed inputs.
- **Independent validators** — pipe agent-produced JSON through any
  JSON Schema validator (e.g. `jsonschema`, `ajv`) before submitting
  to the matcher.

## Files

| File | Purpose |
|---|---|
| `StudentProfile.schema.json` | The applicant's profile (input to `match.py`). |
| `CandidateAdvisor.schema.json` | One candidate PI record (input to `match.py`); embeds `PathEdge`, `OpportunitySignal`, `ProgramProfile`, `ResearchFit`. |
| `FieldProfile.schema.json` | The per-discipline calibration YAMLs in `data/field_profiles/`. |
| `PathEdge.schema.json` | One advisor-to-candidate connection edge. |
| `EvidenceSource.schema.json` | One structured evidence item with `supports_fields` binding. |
| `EvidenceEntry.schema.json` | A signal's evidence (`items` + legacy `sources`). |
| `ResearchFit.schema.json` | The 6-axis structured research fit submodel. |
| `OpportunitySignal.schema.json` | Admit-cycle availability submodel. |
| `ProgramProfile.schema.json` | Per-program difficulty submodel. |
| `MatchResult.schema.json` | One ranked candidate result (output of `match.py`). |
| `StrategyRecommendation.schema.json` | Per-candidate strategy block. |
| `StrategySummary.schema.json` | Portfolio-level rollup. |

## Regenerating

These files are checked in but the **Pydantic source of truth lives in
`phd_matcher/models.py`**. After any model change, regenerate via:

```bash
phdtaketaketake-export-schemas --out schemas/
# or, from a checkout:
python scripts/export_schemas.py --out schemas/
```

CI or pre-commit can run this and check the working tree is clean to
catch drift between Pydantic models and shipped schemas.

## Schema notes

- All models use `extra="forbid"` — JSON with unknown keys fails
  validation.
- Enum-shaped strings (e.g. `school_tier`, `paper_status`,
  `genealogy_relation`, `apply_bucket`) are encoded as `enum` arrays.
- Numeric bounds (`ge=0`, `le=1`, etc.) are encoded as
  `minimum` / `maximum`.
- Nested models appear under `$defs` inside each top-level schema.

## Calibration disclaimer

Generating valid JSON against these schemas does NOT mean the matcher
will produce a meaningful score. The matcher requires **evidence** —
not just well-formed values. See
[`references/data_integrity.md`](../references/data_integrity.md) and
[`references/evidence_schema.md`](../references/evidence_schema.md) for
the strict-mode evidence contract that strict scoring relies on.
