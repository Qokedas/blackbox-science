export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/17408/status ]] && ! grep -q '^State:.*Z' /proc/17408/status; do sleep 5;done
# Independently test the two-screw orthorhombic group: 100 observed; 010 and 003 absent for X1a.
python - <<'PY'
import json
W='/app/work/X1a56c78';j=json.load(open(W+'/fit_1.json'));j['sg']='P 2 21 21';json.dump([j],open(W+'/candidates_sg18.json','w'))
PY
SG_SCAN=0 CANDIDATE_FILE=/app/work/X1a56c78/candidates_sg18.json CANDIDATE_INDEX=0 python /app/work/fit_candidate.py X1a56c78 sg18 .30 > /app/work/X1a56c78/fit_sg18.log 2>&1
mkdir -p /app/work/X1a56c78/gallop_18; cp /app/work/X1a56c78/fit_sg18.xml /app/work/X1a56c78/gallop_18/base.xml
BASE_XML=/app/work/X1a56c78/gallop_18/base.xml SEARCH_TIME=1700 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.24 CONF_RANK=1 python /app/work/search_gallop.py X1a56c78 18 1 --prepare --hscatter --packing > /app/work/X1a56c78/gallop18.log 2>&1
python /app/work/import_gallop.py X1a56c78 18 > /app/work/X1a56c78/import_g18.log 2>&1
python /app/work/refine_obj.py X1a56c78 g18 /app/work/X1a56c78/search_g18/best.xml --scale --tight > /app/work/X1a56c78/refine_g18.log 2>&1
# Independent centrosymmetric hypothesis for the nearly-monoclinic acemetacin/picolinamide lattice.
mkdir -p /app/work/X8a06d7a/gallop_12
python /app/work/extend_low_base.py X8a06d7a /app/work/X8a06d7a/fit_2d1.xml /app/work/X8a06d7a/gallop_12/base.xml > /app/work/X8a06d7a/extend_low12.log 2>&1
BASE_XML=/app/work/X8a06d7a/gallop_12/base.xml HBOND_COEFF=12 BUMP_COEFF=60 START_REFL=100 SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.25 CONF_RANK=1 python /app/work/search_gallop.py X8a06d7a 12 1 --prepare --hscatter --packing > /app/work/X8a06d7a/gallop12.log 2>&1
python /app/work/import_gallop.py X8a06d7a 12 > /app/work/X8a06d7a/import_g12.log 2>&1
python /app/work/refine_obj.py X8a06d7a g12 /app/work/X8a06d7a/search_g12/best.xml --scale --tight --stol=.38 > /app/work/X8a06d7a/refine_g12.log 2>&1
for id in Xd8634a2 Xb7088cf; do
 START_REFL=90 RAMP_REF_EVERY=5 RAMP_REF_STEP=40 SEARCH_TIME=1700 PARTICLES=128 ITERATIONS=400 GALLOP_STOL=.25 CONF_RANK=4 python /app/work/search_gallop.py $id 31 1 --prepare --hscatter --packing > /app/work/$id/gallop31.log 2>&1
 python /app/work/import_gallop.py $id 31 > /app/work/$id/import_g31.log 2>&1
 python /app/work/refine_obj.py $id g31 /app/work/$id/search_g31/best.xml --scale --tight > /app/work/$id/refine_g31.log 2>&1
 done
