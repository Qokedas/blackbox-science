set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=3
id=X1a56c78
for run in 111 112 113 114;do
 (
 BASE_XML=/app/work/$id/gallop_$run/base.xml SEARCH_TIME=320 PARTICLES=128 ITERATIONS=350 GALLOP_STOL=.30 START_REFL=95 BUMP_COEFF=80 HBOND_COEFF=15 CONF_RANK=$((run-111)) python /app/work/search_gallop.py $id $run 1 --prepare --hscatter --packing > /app/work/$id/gallop$run.log 2>&1
 python /app/work/import_gallop.py $id $run > /app/work/$id/import_g$run.log 2>&1
 python /app/work/refine_obj.py $id g$run /app/work/$id/search_g$run/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g$run.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_g$run.cif --check > /app/work/$id/check_g$run.log 2>&1
 python /app/work/check_stereo.py $id /app/work/$id/refined_g$run.cif >> /app/work/$id/check_g$run.log 2>&1
 ) &
done
wait
