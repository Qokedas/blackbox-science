set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/49288/status ]] && ! grep -q '^State:.*Z' /proc/49288/status;do sleep 5;done
W=/app/work/X8a6f5a8
START_FILES=$W/index_fcjnative_TRICLINIC_P_3_partial.json:$W/index_fcjplanes.json OUT_TAG=fcjnew python /app/work/fcj_refine_cells.py > $W/fcj_refine_new.log 2>&1
python - <<'PY'
import json
W='/app/work/X8a6f5a8';r=json.load(open(W+'/candidates_fcjnew.json'));out=[]
for sg in ['P 1','P 1 21 1','C 1 2 1']:
 out += [s for s in r if s['sg']==sg][:2]
# retain old best triclinic and original provisional giant-cell candidate as controls
out += json.load(open(W+'/candidates_fcjrefine.json'))[:1]
s=json.load(open('/app/results/submission/X8a6f5a8.json'));out.append({'cell':list(s['cell'].values()),'sg':s['space_group'],'system':'MONOCLINIC','centering':'P'})
json.dump(out,open(W+'/candidates_fcjfinal.json','w'),indent=1)
PY
for i in 0 1 2 3 4 5 6 7;do
 SG_SCAN=0 CANDIDATE_FILE=$W/candidates_fcjfinal.json CANDIDATE_INDEX=$i python /app/work/fit_candidate.py X8a6f5a8 fcjfinal$i .34 > $W/fit_fcjfinal$i.log 2>&1 || true
done
