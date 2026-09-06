export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export BOND_SIGMA=.004 BOND_DELTA=.006 ANGLE_SIGMA=.5 ANGLE_DELTA=.7 CELL_REL_LIMIT=.003 CELL_ANGLE_LIMIT=.2
python /app/work/refine_obj.py X3f4781b chemH116 /app/work/X3f4781b/search_chemH116/best.xml --scale --tight --stol=.4 > /app/work/X3f4781b/refine_chemH116.log 2>&1
python /app/work/submit.py X3f4781b /app/work/X3f4781b/refined_chemH116.cif --check > /app/work/X3f4781b/check_chemH116.log 2>&1
python /app/work/check_stereo.py X3f4781b /app/work/X3f4781b/refined_chemH116.cif >> /app/work/X3f4781b/check_chemH116.log 2>&1
