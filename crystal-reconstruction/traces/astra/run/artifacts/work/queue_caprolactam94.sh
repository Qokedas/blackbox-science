set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X14a2b08
while [[ ! -f /app/work/$id/refined_g50.json ]] || ! grep -q 'FINISHED' /app/work/$id/refine_g50.log;do sleep 10;done
MAX_CONFORMERS=12 python /app/work/conformer_variants.py $id /app/work/$id/refined_g50.xml /app/work/$id/search_g50/model.json ring94 1 > /app/work/$id/conformers94.log 2>&1
choices=$(python - <<'PY'
import json
x=json.load(open('/app/work/X14a2b08/ring94_choices.json'));print(' '.join(a['tag'] for a in sorted(x,key=lambda a:a['Rw'])[:6]))
PY
)
for tag in $choices;do
 python /app/work/refine_obj.py $id $tag /app/work/$id/search_$tag/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_$tag.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_$tag.cif --check > /app/work/$id/check_$tag.log 2>&1
done
best=$(python - <<'PY'
import glob,os,json
W='/app/work/X14a2b08';x=glob.glob(W+'/refined_ring94c*.json')+[W+'/refined_g50.json'];b=min(x,key=lambda p:json.load(open(p))['Rw']);print(os.path.basename(b)[8:-5])
PY
)
GALLOP_STOL=.29 python /app/work/warm_gallop.py $id 94 /app/work/$id/refined_$best.xml /app/work/$id/search_$best/model.json > /app/work/$id/warm94.log 2>&1
BUMP_COEFF=80 HBOND_COEFF=30 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='1;0;1' python /app/work/search_conditional.py $id 94 95 > /app/work/$id/conditional95.log 2>&1
python /app/work/import_gallop.py $id 95 > /app/work/$id/import_g95.log 2>&1
python /app/work/refine_obj.py $id g95 /app/work/$id/search_g95/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g95.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g95.cif --check > /app/work/$id/check_g95.log 2>&1
