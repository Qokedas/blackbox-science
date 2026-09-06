# Execution runbook (one VM per model)

Everything scientific is frozen before the first model call. Both trial VMs get the same package and the same solver image (by immutable image id, exported once from the build VM and loaded from GCS).

## 0. Build VM (done once)
- Image history: `pxrd-solver:v1` (id b78da392…) failed the harness startup check because the micromamba image exposes python only after activation; `v2` adds `/opt/conda/bin` to PATH. Both attempts with v1 (one per model, 2026-09-06 03:14 UTC) ended as infrastructure failures before any model call and are preserved on the VMs as `runs/<trial>-attempt1-infra`.
- `pxrd-build-0906` built `pxrd-solver:v2` from `environment/` (Dockerfile + TOOLS.md + instruction.md + data/).
- Export: `sudo docker save pxrd-solver:v2 | gzip > /tmp/pxrd-solver-v2.tar.gz`; `gsutil cp` to `gs://qokedas-frontierscience-codex-20260905-401010209795/pxrd-20260906/images/` together with its sha256 and the `docker image inspect` id.

## 1. Provision
```
python execution/cloud.py provision        # creates qkd-0906-pxrd-fable and qkd-0906-pxrd-astra (e2-standard-8, Ubuntu 24.04, bootstrap.sh)
python execution/cloud.py status
```
Wait for `/opt/pxrd/bootstrap.ready` on each VM.

## 2. Deploy the package and the image (each VM)
```
gcloud compute scp --recurse <task_dir> <vm>:/tmp/package ; ssh: sudo mv /tmp/package /opt/pxrd/package (without authoring/, audit/, results/, harness runs)
ssh: gsutil cp gs://.../pxrd-solver-v2.tar.gz /tmp/ && sudo docker load -i /tmp/pxrd-solver-v2.tar.gz
ssh: sudo /opt/pxrd/venv/bin/python /opt/pxrd/package/execution/freeze_contract.py <fable|astra> pxrd-solver:v2
```
`freeze.json` must have identical `package_files` and `image_id` on both VMs (compare the printed sha except the timestamp).

## 3. Preflight (no model call)
- `python -m unittest execution/harness/test_harness.py` on the VM venv (offline suite).
- A 60 s provider smoke: `run_agent.py --smoke --provider ... --budget-seconds 120` (not a scientific call; no benchmark data).
- Grader dry run on the VM: `python tests/grade.py --reference-root /opt/pxrd/package/tests --submission-dir /tmp/empty --out /tmp/g` must print `score 0.000000`; the oracle fixture must print 1.0.

## 4. Credentials and launch
```
python execution/cloud.py inject qkd-0906-pxrd-fable      # writes only ANTHROPIC_API_KEY into /opt/pxrd/provider_credentials.json (0600)
python execution/cloud.py inject qkd-0906-pxrd-astra      # OPENAI_API_KEY
ssh: cd /opt/pxrd && sudo setsid -f bash -c "/opt/pxrd/venv/bin/python /opt/pxrd/package/execution/worker.py /opt/pxrd/jobs/qkd-0906-pxrd-<short>.json > /opt/pxrd/worker-<short>.log 2>&1"
```
The worker runs `execution/harness/run_agent.py` (8 h budget, 4 CPUs, 16 GiB, `--network none`), freezes the container at the deadline, collects `/app/results` and `/app/work`, grades `/app/results/submission` with `tests/grade.py`, writes `runs/<trial>/{result.json,status.json,verifier/}` and a tar.gz of the run, and deletes the credential file.

## 5. Poll (every 20 min)
`ssh: cat /opt/pxrd/runs/<trial>/status.json; tail -2 /opt/pxrd/runs/<trial>/run/trajectory.jsonl` — never touch the container.

## 6. Collect and clean up
```
gcloud compute scp <vm>:/opt/pxrd/qkd-0906-pxrd-<short>.tar.gz  <task_dir>/harness/runs/
gsutil cp ... gs://.../pxrd-20260906/runs/            # second copy
python execution/cloud.py delete <vm>                 # only after the archive is verified locally (sha256)
```
Then: grade, fairness audit, write up.
