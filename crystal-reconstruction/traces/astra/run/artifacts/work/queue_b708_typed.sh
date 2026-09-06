set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 ACCEPTOR_NO_MIN=2.85 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=4
while [[ -r /proc/52927/status ]] && ! grep -q '^State:.*Z' /proc/52927/status;do sleep 5;done
id=Xb7088cf
for bit in 0 1;do
 tag=pyr51m$bit
 python /app/work/refine_obj.py $id $tag /app/work/$id/search_$tag/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_$tag.log 2>&1
done
best=$(python - <<'PY'
import json
W='/app/work/Xb7088cf';print(min(['pyr51m0','pyr51m1'],key=lambda x:json.load(open(W+'/refined_'+x+'.json'))['Rw']))
PY
)
GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 51 /app/work/$id/refined_$best.xml /app/work/$id/search_$best/model.json > /app/work/$id/warm51.log 2>&1
SEARCH_TIME=1400 PARTICLES=128 ITERATIONS=400 BUMP_COEFF=90 HBOND_COEFF=20 START_NPZ=/app/work/$id/gallop_51/warm.npz START_JITTER=.1 START_TOR_JITTER=.5 MACRO_ELITE_FRAC=.4 python /app/work/search_gallop.py $id 51 1 --hscatter --packing > /app/work/$id/gallop51.log 2>&1
python /app/work/import_gallop.py $id 51 > /app/work/$id/import_g51.log 2>&1
python /app/work/refine_obj.py $id g51 /app/work/$id/search_g51/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g51.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g51.cif --check > /app/work/$id/check_g51.log 2>&1
