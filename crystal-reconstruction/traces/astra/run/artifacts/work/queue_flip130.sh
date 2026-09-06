export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
TORSION_BONDS=1:1:3 BUMP_COEFF=.5 python /app/work/enumerate_rotations.py X13023e3 /app/work/X13023e3/refined_g41.xml /app/work/X13023e3/search_g41/model.json pyrflip > /app/work/X13023e3/pyrflip.log 2>&1
python /app/work/refine_obj.py X13023e3 pyrflip /app/work/X13023e3/search_pyrflip/best.xml --scale --tight > /app/work/X13023e3/refine_pyrflip.log 2>&1
