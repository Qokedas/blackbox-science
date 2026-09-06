#!/usr/bin/env python3
"""One preserved physical attempt; runs on its dedicated trial VM.

Layout on the VM: /opt/pxrd/package = the task directory (instruction.md, tests/, execution/harness, environment/),
/opt/pxrd/freeze.json = frozen contract (hashes of package files + image id), /opt/pxrd/jobs/<trial>.json,
/opt/pxrd/provider_credentials.json (one key), /opt/pxrd/runs/<trial>/ = output (run/, verifier/, result.json, status.json).
Grading happens on the host after the container is frozen and collected, with tests/grade.py against tests/truth.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

BASE = Path('/opt/pxrd')
PACKAGE = BASE / 'package'
SUBMISSION_DIR = '/app/results/submission'


def now():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def write(p, o):
    t = p.with_suffix(p.suffix + '.tmp')
    t.write_text(json.dumps(o, indent=2, default=str) + '\n')
    t.replace(p)


def run(argv, **kw):
    return subprocess.run(argv, check=True, capture_output=True, text=True, **kw)


def main(jobpath):
    job = json.loads(jobpath.read_text())
    name = job['trial_id']
    out = BASE / 'runs' / name
    out.mkdir(parents=True, exist_ok=False)
    (out / 'job.json').write_bytes(jobpath.read_bytes())
    status = dict(trial_id=name, phase='preflight', updated_utc=now())
    write(out / 'status.json', status)
    frozen = json.loads((BASE / 'freeze.json').read_text())
    for rel, digest in frozen['package_files'].items():
        if sha(PACKAGE / rel) != digest:
            raise RuntimeError('frozen file changed: ' + rel)
    image = job['image_id']
    if run(['docker', 'image', 'inspect', image, '--format', '{{.Id}}']).stdout.strip() != image:
        raise RuntimeError('image identity')
    instruction = PACKAGE / job['instruction_relative']
    provenance = dict(frozen_contract=frozen, job_sha256=sha(jobpath), instruction_sha256=sha(instruction), trial_id=name, created_utc=now())
    write(out / 'provenance.json', provenance)
    credentials = json.loads((BASE / 'provider_credentials.json').read_text())
    variable = 'OPENAI_API_KEY' if job['provider'] == 'openai' else 'ANTHROPIC_API_KEY'
    assert set(credentials) == {variable}
    env = os.environ.copy()
    env.update(credentials)
    argv = [str(BASE / 'venv/bin/python'), str(PACKAGE / 'execution/harness/run_agent.py'), '--provider', job['provider'], '--model', job['model'],
            '--instruction', str(instruction), '--image', image, '--trial-id', name, '--out', str(out / 'run'),
            '--budget-seconds', str(job['budget_seconds']), '--cpus', str(job['cpus']), '--memory', job['memory'],
            '--submission', SUBMISSION_DIR, '--artifact', '/app/results', '--artifact', '/app/work', '--provenance', str(out / 'provenance.json')]
    status.update(phase='running', started_utc=now())
    write(out / 'status.json', status)
    with (out / 'harness.log').open('wb') as log:
        process = subprocess.Popen(argv, env=env, stdout=log, stderr=subprocess.STDOUT)
        env.pop(variable, None)
        credentials.clear()
        started = time.monotonic()
        while process.poll() is None:
            time.sleep(15)
            if time.monotonic() - started > job['budget_seconds'] + 900:
                process.kill()
                ids = run(['docker', 'ps', '-q', '--filter', 'label=qokedas.trial=' + name]).stdout.split()
                for cid in ids:
                    subprocess.run(['docker', 'kill', cid])
                status['supervisor_failure'] = 'harness exceeded budget plus capture allowance'
                break
        code = process.wait()
    record = json.loads((out / 'run/trial_record.json').read_text()) if (out / 'run/trial_record.json').exists() else {}
    final_dir = out / 'run/artifacts/results/submission'
    gradeout = out / 'verifier'
    gradeout.mkdir()
    refs_ok = all(sha(PACKAGE / rel) == digest for rel, digest in frozen['package_files'].items())
    selected = [x for x in record.get('artifacts', {}).get('submissions', []) if x.get('container_path') == SUBMISSION_DIR]
    binding_ok = len(selected) == 1
    if code != 0 or status.get('supervisor_failure') or not refs_ok or not binding_ok or record.get('execution_status') != 'completed' or record.get('infrastructure_errors'):
        result = dict(status='UNAVAILABLE', score=None, reason='execution_or_contract_failure', harness_exit_code=code, binding_ok=binding_ok, refs_ok=refs_ok,
                      execution_status=record.get('execution_status'), infrastructure_errors=record.get('infrastructure_errors'))
        write(gradeout / 'score_breakdown.json', result)
    else:
        # a healthy timed execution with no submission directory is graded (as empty) and scores zero
        subdir = final_dir if final_dir.is_dir() else out / 'empty_submission'
        subdir.mkdir(exist_ok=True)
        with (out / 'verifier.log').open('wb') as log:
            rc = subprocess.run([str(BASE / 'venv/bin/python'), str(PACKAGE / 'tests/grade.py'), '--reference-root', str(PACKAGE / 'tests'),
                                 '--submission-dir', str(subdir), '--out', str(gradeout)], stdout=log, stderr=subprocess.STDOUT, timeout=3600).returncode
        result = json.loads((gradeout / 'score_breakdown.json').read_text())
        result['grader_exit_code'] = rc
    summary = dict(trial_id=name, model=job['model'], provider=job['provider'], status=result['status'], score=result.get('score'),
                   points=result.get('points'), L_passes=result.get('L_passes'), S_passes=result.get('S_passes'), hedged=result.get('hedged'),
                   termination=record.get('termination'), harness_exit_code=code, finished_utc=now(),
                   elapsed_seconds=(record.get('finished_epoch', 0) - record.get('started_epoch', 0)) if record.get('started_epoch') else None,
                   submission_files=sorted(os.listdir(final_dir)) if final_dir.is_dir() else [])
    write(out / 'result.json', summary)
    status.update(phase='archiving', updated_utc=now())
    write(out / 'status.json', status)
    archive = BASE / (name + '.tar.gz')
    with tarfile.open(archive, 'w:gz') as t:
        t.add(out, arcname=name)
    status.update(phase='complete', updated_utc=now(), archive=str(archive), archive_sha256=sha(archive))
    write(out / 'status.json', status)
    (BASE / 'provider_credentials.json').unlink(missing_ok=True)
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('job', type=Path)
    main(p.parse_args().job)
