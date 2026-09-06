export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/12401/status ]] && ! grep -q '^State:.*Z' /proc/12401/status; do sleep 5; done
# Prioritise an improving zwitterion model before two exploratory difficult cases.
while [[ ! -f /app/work/Xedd9c7b/refined_g11.json ]];do sleep 5;done
GALLOP_STOL=.29 python /app/work/warm_gallop.py Xedd9c7b 50 /app/work/Xedd9c7b/refined_g11.xml /app/work/Xedd9c7b/search_g11/model.json > /app/work/Xedd9c7b/warm50.log 2>&1
HBOND_COEFF=20 SEARCH_TIME=1700 PARTICLES=128 ITERATIONS=400 MACRO_ELITE_FRAC=.30 START_NPZ=/app/work/Xedd9c7b/gallop_50/warm.npz START_JITTER=.06 START_TOR_JITTER=.35 python /app/work/search_gallop.py Xedd9c7b 50 1 --hscatter --packing > /app/work/Xedd9c7b/gallop50.log 2>&1
python /app/work/import_gallop.py Xedd9c7b 50 > /app/work/Xedd9c7b/import_g50.log 2>&1
python /app/work/refine_obj.py Xedd9c7b g50 /app/work/Xedd9c7b/search_g50/best.xml --scale --tight --packing --stol=.37 > /app/work/Xedd9c7b/refine_g50.log 2>&1
# Relax the centrosymmetry hypothesis for the biphenyl salt, without changing
# the submitted space group until there is structural evidence.
GALLOP_STOL=.27 python /app/work/warm_gallop.py X7e382cb 40 /app/work/X7e382cb/search_p1test/best.xml /app/work/X7e382cb/search_p1test/model.json > /app/work/X7e382cb/warm40.log 2>&1
EXACT_BUMP_IMAGES=1 BUMP_COEFF=80 HBOND_COEFF=10 SEARCH_TIME=1500 PARTICLES=128 ITERATIONS=400 MACRO_ELITE_FRAC=.30 START_NPZ=/app/work/X7e382cb/gallop_40/warm.npz START_JITTER=.10 START_TOR_JITTER=.45 python /app/work/search_gallop.py X7e382cb 40 1 --hscatter --packing > /app/work/X7e382cb/gallop40.log 2>&1
python /app/work/import_gallop.py X7e382cb 40 > /app/work/X7e382cb/import_g40.log 2>&1
python /app/work/refine_obj.py X7e382cb g40 /app/work/X7e382cb/search_g40/best.xml --scale --tight --packing --stol=.38 > /app/work/X7e382cb/refine_g40.log 2>&1
for r in 0 5; do
 run=$((20+r))
 SEARCH_TIME=1800 PARTICLES=128 ITERATIONS=450 GALLOP_STOL=.23 CONF_RANK=$r python /app/work/search_gallop.py X238783d $run 1 --prepare --hscatter > /app/work/X238783d/gallop${run}.log 2>&1
 python /app/work/import_gallop.py X238783d $run > /app/work/X238783d/import_g${run}.log 2>&1
 python /app/work/refine_obj.py X238783d g$run /app/work/X238783d/search_g$run/best.xml --scale --tight > /app/work/X238783d/refine_g${run}.log 2>&1
done
