set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/59436/status ]] && ! grep -q '^State:.*Z' /proc/59436/status;do sleep 5;done
id=X3f4781b
best=$(python - <<'PY'
import glob,json,os,subprocess
W='/app/work/X3f4781b';ans=[]
for f in glob.glob(W+'/refined_ninv94m*.json')+[W+'/refined_g83.json']:
 tag=os.path.basename(f)[8:-5]
 if subprocess.run(['python','/app/work/submit.py','X3f4781b',W+'/refined_'+tag+'.cif','--check'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:continue
 if subprocess.run(['python','/app/work/check_stereo.py','X3f4781b',W+'/refined_'+tag+'.cif'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode:continue
 ans.append((json.load(open(f))['Rw'],tag))
print(min(ans)[1])
PY
)
echo BEST_SOURCE $best
GALLOP_STOL=.30 python /app/work/warm_gallop.py $id 97 /app/work/$id/refined_$best.xml /app/work/$id/search_$best/model.json > /app/work/$id/warm97.log 2>&1
BUMP_COEFF=80 HBOND_COEFF=20 PARTICLES=128 ITERATIONS=350 FREE_SCHEDULE='1,3;0;2;1,3;0;2' python /app/work/search_conditional.py $id 97 98 > /app/work/$id/conditional98.log 2>&1
python /app/work/import_gallop.py $id 98 > /app/work/$id/import_g98.log 2>&1
python /app/work/refine_obj.py $id g98 /app/work/$id/search_g98/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_g98.log 2>&1
python /app/work/submit.py $id /app/work/$id/refined_g98.cif --check > /app/work/$id/check_g98.log 2>&1
python /app/work/check_stereo.py $id /app/work/$id/refined_g98.cif >> /app/work/$id/check_g98.log 2>&1
