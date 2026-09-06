import json,sys,subprocess,os
ids=['X35b7fbc','X9af54a2','Xe1fb77b','X13023e3','Xbfc6d2c','X3c176e2','X1a56c78','X238783d','Xd4c1a35','X3f4781b','Xbfeeda9','X2327841','Xdcc971e','X8a06d7a','Xe3a2935','X14a2b08']
for id in ids:
 cs=json.load(open('/app/work/'+id+'/candidates.json'))
 for i,s in enumerate(cs):
  if i>2:continue
  with open(f'/app/work/{id}/fit_{i}.log','w') as f:
   try:p=subprocess.run([sys.executable,'/app/work/fit_candidate.py',id,str(i)],stdout=f,stderr=subprocess.STDOUT,timeout=180)
   except Exception as e:print(id,str(e),flush=True)
  print('DONE',id,i,flush=True)
