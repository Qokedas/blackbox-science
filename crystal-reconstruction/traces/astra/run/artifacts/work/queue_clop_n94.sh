set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
while [[ -r /proc/52928/status ]] && ! grep -q '^State:.*Z' /proc/52928/status;do sleep 5;done
id=X3f4781b
python /app/work/invert_ammonium.py $id /app/work/$id/refined_g83.xml /app/work/$id/search_g83/model.json ninv94 > /app/work/$id/ninv94.log 2>&1
for bits in 00 01 10 11;do
 tag=ninv94m$bits
 python /app/work/check_stereo.py $id /app/work/$id/search_$tag/best.cif > /app/work/$id/stereoseed_$tag.log 2>&1 || true
 python /app/work/refine_obj.py $id $tag /app/work/$id/search_$tag/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_$tag.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_$tag.cif --check > /app/work/$id/check_$tag.log 2>&1 || true
 python /app/work/check_stereo.py $id /app/work/$id/refined_$tag.cif >> /app/work/$id/check_$tag.log 2>&1 || true
done
