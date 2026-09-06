set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=3
while [[ -r /proc/55226/status ]] && ! grep -q '^State:.*Z' /proc/55226/status;do sleep 5;done
id=X1a56c78
for pair in '90 chair84m00' '91 chair84m10';do
 set -- $pair;run=$1;tag=$2
 GALLOP_STOL=.29 python /app/work/warm_gallop.py $id $run /app/work/$id/refined_$tag.xml /app/work/$id/search_$tag/model.json > /app/work/$id/warm$run.log 2>&1
 SEARCH_TIME=800 PARTICLES=128 ITERATIONS=350 BUMP_COEFF=80 HBOND_COEFF=15 MACRO_ELITE_FRAC=.4 START_NPZ=/app/work/$id/gallop_$run/warm.npz START_JITTER=.1 START_TOR_JITTER=.4 python /app/work/search_gallop.py $id $run 1 --hscatter --packing > /app/work/$id/gallop$run.log 2>&1
 python /app/work/import_gallop.py $id $run > /app/work/$id/import_g$run.log 2>&1
 python /app/work/refine_obj.py $id g$run /app/work/$id/search_g$run/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g$run.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_g$run.cif --check > /app/work/$id/check_g$run.log 2>&1
 python /app/work/check_stereo.py $id /app/work/$id/refined_g$run.cif >> /app/work/$id/check_g$run.log 2>&1
done
