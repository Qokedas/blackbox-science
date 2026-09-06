import sys, json, subprocess, os
from concurrent.futures import ThreadPoolExecutor
ids = json.load(open('/app/data/instances.json'))['ids']
sel = sys.argv[1] if len(sys.argv) > 1 else None
if sel: ids = sel.split(',')
nw = int(sys.argv[2]) if len(sys.argv) > 2 else 3
jobs = []
for iid in ids:
    jobs.append((iid, 'monoP', 180))
for iid in ids:
    jobs.append((iid, 'monoC', 90))
for iid in ids:
    jobs.append((iid, 'ortho', 60))
def run(job):
    iid, brav, to = job
    log = f'/app/work/{iid}/g2_{brav}.log'
    with open(log, 'w') as f:
        subprocess.run(['/opt/g2/bin/python', '/app/work/g2index.py', iid, '20', brav, str(to)], stdout=f, stderr=subprocess.STDOUT)
    return job
with ThreadPoolExecutor(nw) as ex:
    for j in ex.map(run, jobs):
        print('done', j, flush=True)
