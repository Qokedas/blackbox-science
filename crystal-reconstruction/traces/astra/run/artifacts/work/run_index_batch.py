import sys,os,json,subprocess,time,concurrent.futures
ids=json.load(open('/app/data/instances.json'))['ids']
priority=['X07806d9','X3c176e2','Xbfc6d2c','Xd4c1a35','X4f6fe58','Xedd9c7b','X7e382cb','Xf8ac963','Xe3a2935']
ids=priority+[x for x in ids if x not in priority]
if len(sys.argv)>1: ids=sys.argv[1:]
env=os.environ.copy();env.update(OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1')
def run(sid):
 jobs=[('CUBIC','P'),('CUBIC','I'),('CUBIC','F'),('TETRAGONAL','P'),('TETRAGONAL','I'),('HEXAGONAL','P'),('RHOMBOEDRAL','P'),('ORTHOROMBIC','P'),('ORTHOROMBIC','C'),('ORTHOROMBIC','I'),('MONOCLINIC','P'),('MONOCLINIC','C')]
 best=0
 for system,cent in jobs:
  out=f'/app/work/{sid}/index_{system}_{cent}_0.json';log=out.replace('.json','.log')
  if os.path.exists(out):s=json.load(open(out))
  else:
   try:
    with open(log,'w') as f: p=subprocess.run([sys.executable,'/app/work/index_one.py',sid,system,cent,'0'],stdout=f,stderr=subprocess.STDOUT,timeout=150 if system=='MONOCLINIC' else 40,env=env)
    s=json.load(open(out)) if os.path.exists(out) else []
   except subprocess.TimeoutExpired:s=[]
  val=max([z['score'] for z in s]+[0]); best=max(best,val)
  print(time.strftime('%H:%M:%S'),sid,system,cent,'best',val,flush=True)
  if val>120:break
 return sid,best
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as ex:
 for r in ex.map(run,ids):print('FINISHED SAMPLE',r,flush=True)
