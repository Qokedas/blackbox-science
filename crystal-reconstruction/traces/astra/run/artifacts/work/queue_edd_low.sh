set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=Xedd9c7b
while [[ -r /proc/36093/status ]] && ! grep -q '^State:.*Z' /proc/36093/status;do sleep 5;done
mkdir -p /app/work/$id/search_low51
cp /app/work/$id/search_g51/model.json /app/work/$id/search_low51/model.json
python /app/work/extend_low_base.py $id /app/work/$id/refined_g51.xml /app/work/$id/search_low51/best.xml > /app/work/$id/extend_low51.log 2>&1
python /app/work/restore_structure_mode.py /app/work/$id/search_low51/best.xml >> /app/work/$id/extend_low51.log 2>&1
GALLOP_STOL=.28 python /app/work/warm_gallop.py $id 52 /app/work/$id/search_low51/best.xml /app/work/$id/search_low51/model.json > /app/work/$id/warm52.log 2>&1
while [[ -r /proc/41254/status ]] && ! grep -q '^State:.*Z' /proc/41254/status;do sleep 5;done
SEARCH_TIME=2000 PARTICLES=128 ITERATIONS=450 BUMP_COEFF=60 HBOND_COEFF=15 START_NPZ=/app/work/$id/gallop_52/warm.npz START_JITTER=.10 START_TOR_JITTER=.4 MACRO_ELITE_FRAC=.40 python /app/work/search_gallop.py $id 52 1 --hscatter --packing > /app/work/$id/gallop52.log 2>&1
python /app/work/import_gallop.py $id 52 > /app/work/$id/import_g52.log 2>&1
python /app/work/refine_obj.py $id g52 /app/work/$id/search_g52/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g52.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g52.cif --check > /app/work/$id/check_g52.log 2>&1
