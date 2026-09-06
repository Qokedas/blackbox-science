#!/usr/bin/env python3
"""Dedicated GCP VMs for the paired trials (one VM per model). Credential values never enter argv or logs.

  cloud.py provision            create the two trial VMs (CPU only, e2-standard-8) with the bootstrap script
  cloud.py inject <vm>          install the provider credential for that VM's model into /opt/pxrd/provider_credentials.json
  cloud.py ssh <vm> '<cmd>'     run a command
  cloud.py status               list the campaign VMs
  cloud.py delete <vm>          delete a VM (after its run has been pulled)
"""
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJECT = 'project-1b2e5a52-4a49-4aa5-863'
ZONE = 'us-central1-a'
CAMPAIGN = 'pxrd-20260906'
SLUG = 'pxrd-blind-solve'
GC = ['gcloud', '--quiet', '--project=' + PROJECT]
JOBS = [('fable', 'anthropic', 'claude-fable-5-1'), ('astra', 'openai', 'gpt-6-astra')]


def run(args, **kw):
    return subprocess.run(args, check=True, text=True, capture_output=True, **kw)


def write(p, o):
    p.write_text(json.dumps(o, indent=2) + '\n')


def state():
    return json.loads((ROOT / 'resources.json').read_text())


def vm_name(short):
    return 'qkd-0906-pxrd-' + short


def ssh(name, command, **kw):
    assert name in [j['name'] for j in state()['jobs']]
    return run(GC + ['compute', 'ssh', name, '--zone=' + ZONE, '--command=' + command], **kw)


def provision():
    p = ROOT / 'resources.json'
    assert not p.exists(), 'resources.json exists: no implicit re-provision'
    s = dict(campaign=CAMPAIGN, project=PROJECT, zone=ZONE, jobs=[])
    for short, provider, model in JOBS:
        s['jobs'].append(dict(name=vm_name(short), short=short, provider=provider, model=model, state='planned'))
    write(p, s)
    for j in s['jobs']:
        try:
            o = run(GC + ['compute', 'instances', 'create', j['name'], '--zone=' + ZONE,
                          '--machine-type=e2-standard-8', '--image-family=ubuntu-2404-lts-amd64', '--image-project=ubuntu-os-cloud',
                          '--boot-disk-size=150GB', '--boot-disk-type=pd-balanced', '--boot-disk-auto-delete',
                          '--scopes=cloud-platform', '--maintenance-policy=MIGRATE',
                          '--max-run-duration=20h', '--instance-termination-action=STOP',
                          '--labels=owner=qokedas,campaign=' + CAMPAIGN,
                          '--metadata-from-file=startup-script=' + str(ROOT / 'bootstrap.sh'),
                          '--format=json(name,id,creationTimestamp,status,machineType)'], timeout=300)
            j.update(state='created', resource=json.loads(o.stdout), created_utc=dt.datetime.now(dt.timezone.utc).isoformat())
        except subprocess.CalledProcessError as e:
            j.update(state='provision_failed', error=e.stderr)
        write(p, s)
        print(json.dumps(j), flush=True)


def inject(name):
    j = next(j for j in state()['jobs'] if j['name'] == name)
    variable = 'ANTHROPIC_API_KEY' if j['provider'] == 'anthropic' else 'OPENAI_API_KEY'
    envfile = ROOT.parents[2] / '.env'
    vals = {}
    for line in envfile.read_text().splitlines():
        if '=' in line and not line.lstrip().startswith('#'):
            k, v = line.split('=', 1)
            vals[k.strip()] = v.strip().strip('"').strip("'")
    value = vals[variable]
    assert value and not any(c in value for c in '\r\n\x00')
    ssh(name, "sudo sh -c 'umask 077; cat > /opt/pxrd/provider_credentials.json'", input=json.dumps({variable: value}), timeout=60)
    print(json.dumps(dict(name=name, credential_installed=True)))


def status():
    o = run(GC + ['compute', 'instances', 'list', '--filter=labels.campaign=' + CAMPAIGN, '--format=table(name,status,machineType.basename(),creationTimestamp)'])
    print(o.stdout)


def delete(name):
    assert name in [j['name'] for j in state()['jobs']]
    o = run(GC + ['compute', 'instances', 'delete', name, '--zone=' + ZONE], timeout=600)
    s = state()
    for j in s['jobs']:
        if j['name'] == name:
            j['state'] = 'deleted'
            j['deleted_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    write(ROOT / 'resources.json', s)
    print('deleted', name)


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'provision':
        provision()
    elif cmd == 'inject':
        inject(sys.argv[2])
    elif cmd == 'ssh':
        p = ssh(sys.argv[2], sys.argv[3], timeout=600)
        print(p.stdout)
        print(p.stderr, file=sys.stderr)
    elif cmd == 'status':
        status()
    elif cmd == 'delete':
        delete(sys.argv[2])
