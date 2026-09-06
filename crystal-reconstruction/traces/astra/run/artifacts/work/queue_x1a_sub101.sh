set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/57998/status ]] && ! grep -q '^State:.*Z' /proc/57998/status;do sleep 5;done
id=X1a56c78
best=$(python - <<'PY'
import json,os
W='/app/work/X1a56c78';a=[(json.load(open(W+'/refined_'+s+'.json'))['Rw'],s) for s in ['g90','g91','chair84m00','chair84m10'] if os.path.isfile(W+'/refined_'+s+'.json')];print(min(a)[1])
PY
)
python /app/work/x1a_subgroup.py $id /app/work/$id/refined_$best.xml /app/work/$id/search_$best/model.json sub101 > /app/work/$id/sub101.log 2>&1
python /app/work/submit.py $id /app/work/$id/search_sub101/best.cif --check > /app/work/$id/check_subseed101.log 2>&1
python /app/work/refine_obj.py $id sub101 /app/work/$id/search_sub101/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_sub101.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_sub101.cif --check > /app/work/$id/check_sub101.log 2>&1
python /app/work/check_stereo.py $id /app/work/$id/refined_sub101.cif >> /app/work/$id/check_sub101.log 2>&1
