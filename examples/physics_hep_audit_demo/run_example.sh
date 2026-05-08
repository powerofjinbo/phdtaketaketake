#!/usr/bin/env bash
# End-to-end demo: physics / HEP applicant default-mode pipeline (audit demo).
#
# Reproduces the 4 output JSONs (discovery_plan / candidates_enriched /
# audit / match) using the bundled fixtures. Default mode (no
# --strict-evidence) so the audit's repair queue is exercised — see
# README.md for what's not in the demo. Requires the repo to be
# installed via `pip install -e .` from the repo root.
#
# Usage (from the repo root):
#   bash examples/physics_hep_audit_demo/run_example.sh

set -euo pipefail

cd "$(dirname "$0")"

echo "=== Stage 1 / 4 — discovery plan ==="
phdtaketaketake-discovery-plan \
  --field physics \
  --schools '["MIT", "UC Berkeley", "Stanford"]' \
  --keywords "ATLAS Higgs precision" \
  > discovery_plan.json
echo "  → discovery_plan.json"

echo
echo "=== Stage 2 / 4 — collect_evidence (fixture mode, offline) ==="
phdtaketaketake-collect-evidence \
  --profile-file profile.json \
  --candidates-file candidates_raw.json \
  --field physics \
  --fixture-dir fixtures/ \
  --out candidates_enriched.json
echo "  → candidates_enriched.json"

# collect_evidence wraps candidates in a top-level object alongside the
# collection_summary. The audit + match CLIs expect a bare candidates
# array, so extract it here.
python -c "
import json, pathlib
data = json.loads(pathlib.Path('candidates_enriched.json').read_text())
pathlib.Path('candidates_for_match.json').write_text(
    json.dumps(data['candidates'], indent=2, ensure_ascii=False) + '\\n'
)
"
echo "  → candidates_for_match.json (bare array, for audit + match)"

echo
echo "=== Stage 3 / 4 — audit (default mode, no --strict-evidence) ==="
phdtaketaketake-audit \
  --profile-file profile.json \
  --candidates-file candidates_for_match.json \
  --field physics \
  > audit.json
echo "  → audit.json"

echo
echo "=== Stage 4 / 4 — match (default mode) ==="
phdtaketaketake-match \
  --profile-file profile.json \
  --candidates-file candidates_for_match.json \
  --field physics --top-k 5 \
  > match.json
echo "  → match.json"

echo
echo "All four stages complete. Output JSONs sit alongside this script."
