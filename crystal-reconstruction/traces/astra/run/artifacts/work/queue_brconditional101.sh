set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CARBONYL_OO_MIN=2.85 ACCEPTOR_NO_MIN=2.80 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=4
while [[ -r /proc/43321/status ]] && ! grep -q '^State:.*Z' /proc/43321/status;do sleep 5;done
id=X4f6fe58
GALLOP_STOL=.30 python /app/work/warm_gallop.py $id 100 /app/work/$id/refined_g84.xml /app/work/$id/search_g84/model.json > /app/work/$id/warm100.log 2>&1
BUMP_COEFF=90 HBOND_COEFF=25 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='0;1;0;1' python /app/work/search_conditional.py $id 100 101 > /app/work/$id/conditional101.log 2>&1
python /app/work/import_gallop.py $id 101 > /app/work/$id/import_g101.log 2>&1
python /app/work/refine_obj.py $id g101 /app/work/$id/search_g101/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g101.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g101.cif --check > /app/work/$id/check_g101.log 2>&1
