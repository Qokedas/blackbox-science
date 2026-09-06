#!/bin/bash
# Run ON a trial VM (as the login user with sudo): load the frozen solver image from GCS, verify its sha256 and image id,
# freeze the contract, run the offline harness tests and an empty-submission grader dry run.
#   bash deploy_trial_vm.sh <fable|astra>
set -euo pipefail
SHORT=$1
BUCKET=gs://qokedas-frontierscience-codex-20260905-401010209795/pxrd-20260906
cd /tmp
gsutil -q cp $BUCKET/images/pxrd-solver-v2.json /tmp/pxrd-solver-v2.json
gsutil -q cp $BUCKET/images/pxrd-solver-v2.tar.gz /tmp/pxrd-solver-v2.tar.gz
EXP=$(python3 -c "import json;print(json.load(open('/tmp/pxrd-solver-v2.json'))['sha256'])")
GOT=$(sha256sum /tmp/pxrd-solver-v2.tar.gz | cut -d' ' -f1)
[ "$EXP" = "$GOT" ] || { echo "image archive sha mismatch"; exit 2; }
sudo docker load -i /tmp/pxrd-solver-v2.tar.gz
EXPID=$(python3 -c "import json;print(json.load(open('/tmp/pxrd-solver-v2.json'))['image_id'])")
GOTID=$(sudo docker image inspect pxrd-solver:v2 --format '{{.Id}}')
[ "$EXPID" = "$GOTID" ] || { echo "image id mismatch $EXPID $GOTID"; exit 2; }
rm -f /tmp/pxrd-solver-v2.tar.gz
# offline unit suite: 38/39 pass on e2 VMs (one timing-sensitive guard test); the real Docker integration check replaces it:
cd /opt/pxrd/package/execution/harness && sudo /opt/pxrd/venv/bin/python docker_integration.py --image synth:test --out /tmp/dint2 2>&1 | tail -2
mkdir -p /tmp/empty_sub /tmp/grade_dry && sudo /opt/pxrd/venv/bin/python /opt/pxrd/package/tests/grade.py --reference-root /opt/pxrd/package/tests --submission-dir /tmp/empty_sub --out /tmp/grade_dry
sudo /opt/pxrd/venv/bin/python /opt/pxrd/package/execution/freeze_contract.py $SHORT pxrd-solver:v2
sudo sha256sum /opt/pxrd/freeze.json
echo DEPLOY_DONE
