set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X8a06d7a
mkdir -p /app/work/$id/gallop_74
python /app/work/extend_low_base.py $id /app/work/$id/fit_tri_single.xml /app/work/$id/gallop_74/transfer_base.xml > /app/work/$id/extend74.log 2>&1
TRANSFER_BASE=/app/work/$id/gallop_74/transfer_base.xml python /app/work/transfer_acm.py X263b09a $id g91 transfer74 > /app/work/$id/transfer74.log 2>&1
GALLOP_STOL=.27 python /app/work/warm_gallop.py $id 74 /app/work/$id/search_transfer74/best.xml /app/work/$id/search_transfer74/model.json > /app/work/$id/warm74.log 2>&1
SEARCH_TIME=1500 PARTICLES=128 ITERATIONS=350 BUMP_COEFF=70 HBOND_COEFF=15 START_NPZ=/app/work/$id/gallop_74/warm.npz START_JITTER=.1 START_TOR_JITTER=.4 MACRO_ELITE_FRAC=.4 python /app/work/search_gallop.py $id 74 1 --hscatter --packing > /app/work/$id/gallop74.log 2>&1
python /app/work/import_gallop.py $id 74 > /app/work/$id/import_g74.log 2>&1
python /app/work/refine_obj.py $id g74 /app/work/$id/search_g74/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g74.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g74.cif --check > /app/work/$id/check_g74.log 2>&1
