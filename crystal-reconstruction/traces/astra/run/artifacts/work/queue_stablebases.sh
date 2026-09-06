export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MAX_STOL=.30
for spec in 'X3f4781b 0 P 1 21 1' 'X14a2b08 4 P -1'; do
 read -r id tag sg <<< "$spec"
 cp /app/work/$id/base.xml /app/work/$id/base_badold.xml
 python /app/work/create_stable_base.py $id $tag "$sg" --submit > /app/work/$id/basestable.log 2>&1
 python /app/work/audit_base.py $id >> /app/work/$id/basestable.log 2>&1
done
