#!/bin/bash
# Verifier entry point (separate container, no network). Grades /final/submission (or $PXRD_SUBMISSION_DIR)
# against /tests/truth and writes /logs/verifier/{score_breakdown.json,reward.txt}. Exit 2 = UNAVAILABLE (no reward).
set -uo pipefail
out=${PXRD_LOG_DIR:-/logs/verifier}
tests=${PXRD_TESTS_DIR:-/tests}
sub=${PXRD_SUBMISSION_DIR:-/final/submission}
mkdir -p "$out"
rm -f "$out/reward.txt" "$out/score_breakdown.json"
if ! command -v python3 >/dev/null 2>&1; then
  echo '{"status":"UNAVAILABLE","score":null,"reason":"python3 missing"}' > "$out/score_breakdown.json"; exit 2
fi
python3 "$tests/grade.py" --reference-root "$tests" --submission-dir "$sub" --out "$out"
rc=$?
if [ "$rc" -ne 0 ]; then
  rm -f "$out/reward.txt"
  [ -f "$out/score_breakdown.json" ] || echo '{"status":"UNAVAILABLE","score":null,"reason":"evaluator failed"}' > "$out/score_breakdown.json"
  exit 2
fi
