set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
id=X3f4781b
for bits in 00 01 10 11;do
 (
 tag=ninv110m$bits
 python /app/work/refine_obj.py $id $tag /app/work/$id/search_$tag/best.xml --scale --tight --stol=.4 > /app/work/$id/refine_$tag.log 2>&1
 python /app/work/submit.py $id /app/work/$id/refined_$tag.cif --check > /app/work/$id/check_$tag.log 2>&1
 python /app/work/check_stereo.py $id /app/work/$id/refined_$tag.cif >> /app/work/$id/check_$tag.log 2>&1
 ) &
done
wait
