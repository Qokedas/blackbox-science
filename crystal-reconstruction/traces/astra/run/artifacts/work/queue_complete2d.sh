export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 NSPUR=2 VMIN=1050 VMAX=1700
PLANE_MAX=17.3 python /app/work/complete_2d.py X14a2b08 4 > /app/work/X14a2b08/complete2d.log 2>&1
PLANE_MAX=17.9 python /app/work/complete_2d.py X8a06d7a 0 > /app/work/X8a06d7a/complete2d.log 2>&1
PLANE_MAX=16.0 python /app/work/complete_2d.py X263b09a 0 > /app/work/X263b09a/complete2d.log 2>&1
