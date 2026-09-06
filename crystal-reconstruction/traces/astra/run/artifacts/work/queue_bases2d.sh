export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
MAX_STOL=.30 python /app/work/create_base.py X263b09a 2d0 'P -1' --submit > /app/work/X263b09a/base2d.log 2>&1
MAX_STOL=.30 python /app/work/create_base.py X8a06d7a 2d1 'P -1' --submit > /app/work/X8a06d7a/base2d.log 2>&1
