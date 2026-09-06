export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/16777/status ]] && ! grep -q '^State:.*Z' /proc/16777/status; do sleep 5;done
# The two C=N hydrazone configurations are unspecified in the supplied SMILES.
# G11 uses the first; this is the independent second configuration.
SEARCH_TIME=1800 PARTICLES=160 ITERATIONS=450 GALLOP_STOL=.24 CONF_RANK=0 python /app/work/search_gallop.py X019b9a4 12 1 --prepare --hscatter > /app/work/X019b9a4/gallop12.log 2>&1
python /app/work/import_gallop.py X019b9a4 12 > /app/work/X019b9a4/import_g12.log 2>&1
python /app/work/refine_obj.py X019b9a4 g12 /app/work/X019b9a4/search_g12/best.xml --scale --tight --packing > /app/work/X019b9a4/refine_g12.log 2>&1
