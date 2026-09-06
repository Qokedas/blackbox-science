set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 CARBONYL_OO_MIN=2.85 ACCEPTOR_NO_MIN=2.80 HBOND_DIRECTIONAL=1 HBOND_ANGLE_WEIGHT=4
id=X4f6fe58
MAX_CONFORMERS=8 python /app/work/conformer_variants.py $id /app/work/$id/refined_g101.xml /app/work/$id/search_g101/model.json conf105 0 12,13,14,16,17,18 > /app/work/$id/conf105.log 2>&1
choices=$(python - <<'PY'
import json
x=json.load(open('/app/work/X4f6fe58/conf105_choices.json'));print(' '.join(a['tag'] for a in sorted(x,key=lambda a:a['Rw'])[:4]))
PY
)
for tag in $choices;do
 if [[ -f /app/work/$id/refined_$tag.json ]] && grep -q FINISHED /app/work/$id/refine_$tag.log; then continue; fi
 python /app/work/refine_obj.py $id $tag /app/work/$id/search_$tag/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_$tag.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_$tag.cif --check > /app/work/$id/check_$tag.log 2>&1
done
best=$(python - <<'PY'
import json,glob,os
W='/app/work/X4f6fe58';x=glob.glob(W+'/refined_conf105c*.json')+[W+'/refined_g101.json'];print(os.path.basename(min(x,key=lambda f:json.load(open(f))['Rw']))[8:-5])
PY
)
echo FIRST_BEST $best
MAX_CONFORMERS=8 python /app/work/conformer_variants.py $id /app/work/$id/refined_$best.xml /app/work/$id/search_$best/model.json conf106 1 12,13,14,16,17,18 > /app/work/$id/conf106.log 2>&1
choices=$(python - <<'PY'
import json
x=json.load(open('/app/work/X4f6fe58/conf106_choices.json'));print(' '.join(a['tag'] for a in sorted(x,key=lambda a:a['Rw'])[:3]))
PY
)
for tag in $choices;do
 if [[ -f /app/work/$id/refined_$tag.json ]] && grep -q FINISHED /app/work/$id/refine_$tag.log; then continue; fi
 python /app/work/refine_obj.py $id $tag /app/work/$id/search_$tag/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_$tag.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_$tag.cif --check > /app/work/$id/check_$tag.log 2>&1
done
