set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for pid in 16742 45980;do
 while [[ -r /proc/$pid/status ]] && ! grep -q '^State:.*Z' /proc/$pid/status;do sleep 5;done
done
for id in X263b09a X14a2b08 X1db5091;do
 old=$(python - "$id" <<'PY'
import json,sys,os,subprocess
W='/app/work/'+sys.argv[1];ans=[]
for run in ['g11','g70','g72','g91','1']:
 if not os.path.exists(W+'/refined_'+run+'.json'):continue
 r=subprocess.run([sys.executable,'/app/work/submit.py',sys.argv[1],W+'/refined_'+run+'.cif','--check'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 if r.returncode==0:ans.append((json.load(open(W+'/refined_'+run+'.json'))['Rw'],run))
print(min(ans)[1])
PY
 )
 python /app/work/split_synthon.py "$id" "$old" split50 > /app/work/$id/split50.log 2>&1
 GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 50 /app/work/$id/search_split50/best.xml /app/work/$id/search_split50/model.json > /app/work/$id/warm50.log 2>&1
 SEARCH_TIME=1500 PARTICLES=128 ITERATIONS=400 BUMP_COEFF=70 HBOND_COEFF=15 MACRO_ELITE_FRAC=.35 START_NPZ=/app/work/$id/gallop_50/warm.npz START_JITTER=.08 START_TOR_JITTER=.35 python /app/work/search_gallop.py $id 50 1 --hscatter --packing > /app/work/$id/gallop50.log 2>&1
 python /app/work/import_gallop.py $id 50 > /app/work/$id/import_g50.log 2>&1
 python /app/work/refine_obj.py $id g50 /app/work/$id/search_g50/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g50.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_g50.cif --check > /app/work/$id/check_g50.log 2>&1
done
