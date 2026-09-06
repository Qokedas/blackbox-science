export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/16742/status ]] && ! grep -q '^State:.*Z' /proc/16742/status; do sleep 5;done
for id in X263b09a X14a2b08 X1db5091; do
 old=$(python - "$id" <<'PY'
import json,sys,os
W='/app/work/'+sys.argv[1]
ans=[]
for run in ['g11','1']:
 if os.path.exists(W+'/refined_'+run+'.json'):ans.append((json.load(open(W+'/refined_'+run+'.json'))['Rw'],run))
print(min(ans)[1])
PY
)
 GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 50 /app/work/$id/refined_$old.xml /app/work/$id/search_$old/model.json > /app/work/$id/warm50.log 2>&1
 SEARCH_TIME=1500 PARTICLES=128 ITERATIONS=400 MACRO_ELITE_FRAC=.30 START_NPZ=/app/work/$id/gallop_50/warm.npz START_JITTER=.05 START_TOR_JITTER=.30 python /app/work/search_gallop.py $id 50 1 --hscatter --packing > /app/work/$id/gallop50.log 2>&1
 python /app/work/import_gallop.py $id 50 > /app/work/$id/import_g50.log 2>&1
 python /app/work/refine_obj.py $id g50 /app/work/$id/search_g50/best.xml --scale --tight --stol=.35 > /app/work/$id/refine_g50.log 2>&1
 done
