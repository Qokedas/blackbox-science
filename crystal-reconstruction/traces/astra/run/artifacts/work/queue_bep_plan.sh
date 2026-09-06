export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
TORSION_BONDS=0:11:19 SAVE_ALL=1 python /app/work/enumerate_rotations.py Xeb393f9 /app/work/Xeb393f9/refined_plan.xml /app/work/Xeb393f9/search_plan/model.json pyr > /app/work/Xeb393f9/pyr.log 2>&1
for run in pyrm0 pyrm1; do
 python /app/work/refine_obj.py Xeb393f9 $run /app/work/Xeb393f9/search_$run/best.xml --scale --tight --stol=.38 > /app/work/Xeb393f9/refine_$run.log 2>&1
 python /app/work/submit.py Xeb393f9 /app/work/Xeb393f9/refined_$run.cif --check > /app/work/Xeb393f9/check_$run.log 2>&1
 python /app/work/check_stereo.py Xeb393f9 /app/work/Xeb393f9/refined_$run.cif >> /app/work/Xeb393f9/check_$run.log 2>&1
 done
