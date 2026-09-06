set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/22050/status ]] && ! grep -q '^State:.*Z' /proc/22050/status; do sleep 5;done
python /app/work/extend_low_base.py X3f4781b /app/work/X3f4781b/refined_g11.xml /app/work/X3f4781b/refined_low11.xml > /app/work/X3f4781b/extend_low11.log 2>&1
GALLOP_STOL=.26 python /app/work/warm_gallop.py X3f4781b 50 /app/work/X3f4781b/refined_low11.xml /app/work/X3f4781b/search_g11/model.json > /app/work/X3f4781b/warm50.log 2>&1
HBOND_COEFF=10 SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=400 START_REFL=110 RAMP_REF_EVERY=4 RAMP_REF_STEP=40 START_NPZ=/app/work/X3f4781b/gallop_50/warm.npz START_JITTER=.09 START_TOR_JITTER=.40 MACRO_ELITE_FRAC=.30 python /app/work/search_gallop.py X3f4781b 50 2 --hscatter --packing > /app/work/X3f4781b/gallop50.log 2>&1
python /app/work/import_gallop.py X3f4781b 50 > /app/work/X3f4781b/import_g50.log 2>&1
python /app/work/refine_obj.py X3f4781b g50 /app/work/X3f4781b/search_g50/best.xml --scale --tight > /app/work/X3f4781b/refine_g50.log 2>&1
