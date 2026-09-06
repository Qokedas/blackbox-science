#!/bin/bash
# Run fox_solve.py for every instance in parallel inside the tools image (calibration VM).
#   run_batch.sh <mode oracle|routine> <task_dir_on_host> <out_root_on_host> <parallel> <runs> <steps> <max_minutes> [ids...]
# Each instance runs single-threaded (OMP_NUM_THREADS=1) under --cpus=1 per container slot via xargs -P.
set -uo pipefail
MODE=$1; TASK=$2; OUT=$3; PAR=$4; RUNS=$5; STEPS=$6; MAXMIN=$7; shift 7
mkdir -p "$OUT"
if [ $# -gt 0 ]; then IDS="$*"; else IDS=$(python3 -c "import json;print(' '.join(json.load(open('$TASK/tests/manifest.json'))['ids']))"); fi
echo "$IDS" | tr ' ' '\n' | xargs -P "$PAR" -I{} bash -c '
  id={}; mkdir -p '"$OUT"'/$id
  sudo docker run --rm --cpus=1 -e OMP_NUM_THREADS=1 -v '"$TASK"':/t -v '"$OUT"':/o pxrd-tools bash -lc "cd /t && python authoring/evidence/fox_solve.py --mode '"$MODE"' --instance environment/data/instances/$id --truth tests/truth/$id.json --grader tests --out /o/$id --runs '"$RUNS"' --steps '"$STEPS"' --max-minutes '"$MAXMIN"'" > '"$OUT"'/$id/stdout.log 2>&1
  echo "done $id $(date -u +%H:%M:%S)"
'
echo BATCH_DONE
