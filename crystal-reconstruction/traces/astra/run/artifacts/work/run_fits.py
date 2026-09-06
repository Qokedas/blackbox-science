import json,sys,subprocess,concurrent.futures,os
ids=json.load(open('/app/data/instances.json'))['ids'];jobs=[]
for id in ids:
 cs=json.load(open('/app/work/'+id+'/candidates.json'))
 for i,s in enumerate(cs[:2]):
  if s['score']>10 and not os.path.exists(f'/app/work/{id}/fit_{i}.json'):jobs.append((id,i))
def run(v):
 id,i=v
 with open(f'/app/work/{id}/fit_{i}.log','w') as f:
  try:p=subprocess.run([sys.executable,'/app/work/fit_candidate.py',id,str(i)],stdout=f,stderr=subprocess.STDOUT,timeout=300)
  except Exception as e:print(id,str(e),flush=True)
 print('DONE',id,i,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(run,jobs))
