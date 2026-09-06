#!/usr/bin/env python3
"""Freeze the pretrial contract on a trial VM, before any scientific API call.

Hashes every file the trial depends on (instruction, tests/, environment/ inputs, harness, execution scripts),
records the immutable solver image id, and writes /opt/pxrd/freeze.json and /opt/pxrd/jobs/<trial>.json.
Run once per VM (refuses to overwrite). The same package must be frozen on both VMs; compare the two freeze.json.
Usage: freeze_contract.py <short: fable|astra> <image_tag>
"""
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE = Path('/opt/pxrd')
PACKAGE = BASE / 'package'
JOBS = {'fable': ('anthropic', 'claude-fable-5-1'), 'astra': ('openai', 'gpt-6-astra')}


def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def main(short, image_tag):
    assert not (BASE / 'freeze.json').exists(), 'freeze.json exists: no implicit contract revision'
    provider, model = JOBS[short]
    files = {}
    for rel in ['instruction.md', 'task.toml']:
        files[rel] = sha(PACKAGE / rel)
    for folder in ['tests', 'environment', 'execution/harness']:
        for p in sorted((PACKAGE / folder).rglob('*')):
            if p.is_file() and '__pycache__' not in p.parts:
                files[str(p.relative_to(PACKAGE))] = sha(p)
    for name in ['worker.py', 'freeze_contract.py']:
        files['execution/' + name] = sha(PACKAGE / 'execution' / name)
    image_id = subprocess.check_output(['docker', 'image', 'inspect', image_tag, '--format', '{{.Id}}'], text=True).strip()
    frozen = dict(schema_version=1, frozen_utc=dt.datetime.now(dt.timezone.utc).isoformat(), slug='pxrd-blind-solve',
                  package_files=files, image_id=image_id, image_tag=image_tag,
                  scoring=dict(points_L=1, points_S=2, per_instance=3, n_instances=json.loads((PACKAGE / 'tests/manifest.json').read_text())['n'],
                               L_length_tol=0.01, L_angle_tol_deg=1.0, S_rmsd_A=0.35, S_dmax_A=1.0),
                  resource_contract=dict(cpus=4, memory_gib=16, scientific_seconds=28800, poll_seconds=1200, gpu=None),
                  model_protocol=dict(reasoning_effort='max', response_output_tokens=64000),
                  change_policy='No scientific contract changes after this freeze. Infrastructure replacements are declared before any new model call and the original attempt is preserved.')
    (BASE / 'freeze.json').write_text(json.dumps(frozen, indent=2) + '\n')
    jobs = BASE / 'jobs'
    jobs.mkdir(exist_ok=True)
    name = 'qkd-0906-pxrd-' + short
    (jobs / (name + '.json')).write_text(json.dumps(dict(trial_id=name, provider=provider, model=model, kind='scientific_trial', image_id=image_id,
                                                          instruction_relative='instruction.md', budget_seconds=28800, cpus=4, memory='16g'), indent=2) + '\n')
    digest = sha(BASE / 'freeze.json')
    print(json.dumps(dict(frozen_sha256=digest, image_id=image_id, n_files=len(files), job=name)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
