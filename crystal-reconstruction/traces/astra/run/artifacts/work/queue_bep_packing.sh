export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/18059/status ]] && ! grep -q '^State:.*Z' /proc/18059/status; do sleep 5; done
for num in 0 1; do
 run=$((50+num));
 GALLOP_STOL=.30 python /app/work/warm_gallop.py Xeb393f9 $run /app/work/Xeb393f9/refined_pyrm$num.xml /app/work/Xeb393f9/search_pyrm$num/model.json > /app/work/Xeb393f9/warm$run.log 2>&1
 SEARCH_TIME=850 PARTICLES=96 ITERATIONS=350 MACRO_ELITE_FRAC=.25 EXACT_BUMP_IMAGES=1 START_NPZ=/app/work/Xeb393f9/gallop_$run/warm.npz START_JITTER=.04 START_TOR_JITTER=.25 python /app/work/search_gallop.py Xeb393f9 $run 1 --hscatter --packing > /app/work/Xeb393f9/gallop$run.log 2>&1
 python /app/work/import_gallop.py Xeb393f9 $run > /app/work/Xeb393f9/import_g$run.log 2>&1
 python /app/work/refine_obj.py Xeb393f9 g$run /app/work/Xeb393f9/search_g$run/best.xml --scale --tight > /app/work/Xeb393f9/refine_g$run.log 2>&1
 python /app/work/submit.py Xeb393f9 /app/work/Xeb393f9/refined_g$run.cif --check > /app/work/Xeb393f9/check_g$run.log 2>&1
 python /app/work/check_stereo.py Xeb393f9 /app/work/Xeb393f9/refined_g$run.cif >> /app/work/Xeb393f9/check_g$run.log 2>&1
 done
