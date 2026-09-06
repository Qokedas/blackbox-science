export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_raw.json NPEAK=18 NSPUR=0 INDEX_SCORE=55 INDEX_DEPTH=6 LMAX=34 TTHERR=.025 MAXERR=.06 INDEX_TAG=strict
while [[ -r /proc/5100/status ]] && ! grep -q '^State:.*Z' /proc/5100/status; do sleep 5; done
for shift in 0 0.02 -0.02; do
 PEAK_SKIP=1 NPEAK=20 TTHSHIFT=$shift timeout 500 python /app/work/index_one.py X1db5091 TRICLINIC P 3 1000 1800 > /app/work/X1db5091/index_raw_strict_$shift.log 2>&1
done
for center in P C; do
 PEAK_SKIP=1 NPEAK=20 TTHSHIFT=0 timeout 220 python /app/work/index_one.py X1db5091 MONOCLINIC $center 3 1800 6000 > /app/work/X1db5091/index_raw_large_MONOCLINIC_$center.log 2>&1
done
python /app/work/collect_candidates.py X1db5091 X8a6f5a8 Xebbd488 Xb7088cf Xedd9c7b
SEARCH_TIME=2600 MC_STEPS=4000000 TARGET_RW=.07 python /app/work/search_obj.py Xeb393f9 1 1 --rescale > /app/work/Xeb393f9/search1.log 2>&1
python /app/work/refine_obj.py Xeb393f9 1 /app/work/Xeb393f9/search_1/best.xml --scale --tight > /app/work/Xeb393f9/refine_1.log 2>&1
