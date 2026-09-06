import sys,os,json,subprocess,time,concurrent.futures
ids=json.load(open('/app/data/instances.json'))['ids']
if len(sys.argv)>1:ids=sys.argv[1:]
else:
 ids=[x for x in ids if not json.load(open('/app/work/'+x+'/candidates.json')) or json.load(open('/app/work/'+x+'/candidates.json'))[0]['score']<16]
mode=2
jobs=[(s,'ORTHOROMBIC','P') for s in ids]+[(s,'MONOCLINIC','P') for s in ids]+[(s,'MONOCLINIC','C') for s in ids]
def run(job):
 s,sy,ce=job;out=f'/app/work/{s}/index_{sy}_{ce}_{mode}.json';log=out.replace('.json','.log')
 with open(log,'w') as f:
  try:subprocess.run([sys.executable,'/app/work/index_one.py',s,sy,ce,str(mode)],stdout=f,stderr=subprocess.STDOUT,timeout=240)
  except Exception as e:print(s,sy,str(e),flush=True)
 if os.path.exists(out):
  sols=json.load(open(out));val=max([s['score'] for s in sols]+[0]);print(s,sy,ce,val,flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:list(ex.map(run,jobs))
