import sys,re,json,os
sid=sys.argv[1];tag=sys.argv[2] if len(sys.argv)>2 else 'TRICLINIC_P_3';W='/app/work/'+sid
text=open(W+'/index_'+tag+'.log').read();pat=r'Solution\s*\?\s*a=\s*([\d.]+),?\s*b=\s*([\d.]+),?\s*c=\s*([\d.]+),?\s*alpha=\s*([\d.]+),?\s*beta=\s*([\d.]+),?\s*gamma=\s*([\d.]+),?\s*V=\s*([\d.]+),?\s*score=\s*([\d.]+)';rows=[]
tokens=tag.split('_');ks=next(i for i,t in enumerate(tokens) if t in ['TRICLINIC','MONOCLINIC','ORTHOROMBIC','TETRAGONAL','HEXAGONAL','CUBIC','RHOMBOEDRAL']);system=tokens[ks];centering=tokens[ks+1];mode=next((int(t) for t in tokens[ks+2:] if t.isdigit()),9)
for ma in re.finditer(pat,text):
 v=list(map(float,ma.groups()));rows.append({'cell':v[:6],'volume':v[6],'score':v[7],'system':system,'centering':centering,'mode':mode})
rows.sort(key=lambda s:-s['score']);out=[];seen=set()
for r in rows:
 key=tuple(round(x,2) for x in r['cell'])
 if key in seen:continue
 seen.add(key);out.append(r)
 if len(out)>=100:break
json.dump(out,open(W+'/index_'+tag+'_partial.json','w'),indent=1)
print(sid,len(out),out[:4])
