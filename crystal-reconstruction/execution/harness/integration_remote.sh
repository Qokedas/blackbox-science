#!/bin/bash
# Explicit synthetic infrastructure verification only. No API calls or benchmark data.
set -euo pipefail
trial_test_dir=$(cd -- "$(dirname -- "$0")" && pwd)
python3 -m venv "$trial_test_dir/test-venv"
"$trial_test_dir/test-venv/bin/pip" install --disable-pip-version-check -r "$trial_test_dir/requirements.txt" > "$trial_test_dir/integration-pip.log" 2>&1
mkdir -p "$trial_test_dir/synthetic-image"
cat > "$trial_test_dir/synthetic-image/Dockerfile" <<'EOF'
FROM python:3.11-slim
WORKDIR /app
EOF
trap 'docker image rm qokedas-harness-synthetic:0905 >/dev/null 2>&1 || true' EXIT
docker build -t qokedas-harness-synthetic:0905 "$trial_test_dir/synthetic-image" > "$trial_test_dir/integration-build.log" 2>&1
"$trial_test_dir/test-venv/bin/python" "$trial_test_dir/docker_integration.py" --image qokedas-harness-synthetic:0905 --out "$trial_test_dir/integration-results"
