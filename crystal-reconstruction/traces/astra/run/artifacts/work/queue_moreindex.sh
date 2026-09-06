export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_raw.json NPEAK=18 NSPUR=1 INDEX_SCORE=60 INDEX_DEPTH=6 LMAX=40 TTHERR=.025 MAXERR=.06 INDEX_TAG=zeroscan
while [[ -r /proc/8306/status ]] && ! grep -q '^State:.*Z' /proc/8306/status; do sleep 5; done
for shift in -0.2 -0.1 0.1 0.2; do
 for system in ORTHOROMBIC MONOCLINIC; do
  for center in P C; do
   TTHSHIFT=$shift timeout 90 python /app/work/index_one.py Xedd9c7b $system $center 4 450 2800 > /app/work/Xedd9c7b/index_zero_${shift}_${system}_${center}.log 2>&1
  done
 done
done
for id in Xedd9c7b Xb7088cf; do
 for tag in raw_TRICLINIC_P raw_MONOCLINIC_P; do python /app/work/parse_index_log.py $id $tag; done
 python /app/work/collect_candidates.py $id
 for idx in 0 1 2 3; do python /app/work/fit_candidate.py $id $idx .3 > /app/work/$id/fit_$idx.log 2>&1; done
done
