export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
for id in X8a6f5a8 Xebbd488; do
 if [[ $id == X8a6f5a8 ]]; then
  for idx in 0 1 2 3; do python /app/work/fit_candidate.py $id $idx .27 > /app/work/$id/fit_$idx.log 2>&1; done
 else
  CANDIDATE_FILE=/app/work/$id/index_MONOCLINIC_C_4_1200_6500_z0_peaks_raw.json CANDIDATE_INDEX=0 python /app/work/fit_candidate.py $id rawC0 .27 > /app/work/$id/fit_rawC0.log 2>&1
  for idx in 0 1 2; do python /app/work/fit_candidate.py $id $idx .27 > /app/work/$id/fit_$idx.log 2>&1; done
 fi
done
