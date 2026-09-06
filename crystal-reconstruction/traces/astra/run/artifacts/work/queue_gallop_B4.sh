export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/12401/status ]] && ! grep -q '^State:.*Z' /proc/12401/status; do sleep 5; done
for r in 0 5 12; do
 run=$((20+r))
 SEARCH_TIME=2300 PARTICLES=128 ITERATIONS=450 GALLOP_STOL=.23 CONF_RANK=$r python /app/work/search_gallop.py X238783d $run 1 --prepare --hscatter > /app/work/X238783d/gallop${run}.log 2>&1
 python /app/work/import_gallop.py X238783d $run > /app/work/X238783d/import_g${run}.log 2>&1
 python /app/work/refine_obj.py X238783d g$run /app/work/X238783d/search_g$run/best.xml --scale --tight > /app/work/X238783d/refine_g${run}.log 2>&1
done
