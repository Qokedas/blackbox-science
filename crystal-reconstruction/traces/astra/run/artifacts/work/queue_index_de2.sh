export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_raw.json NPEAK=23 MAXITER=1000 TRIALS=10 INDEX_TIME=400 NSPUR=1 INDEX_TAG=de_raw
python /app/work/index_de.py X8a06d7a > /app/work/X8a06d7a/de_raw.log 2>&1
python /app/work/index_de.py X14a2b08 --fixed-c > /app/work/X14a2b08/de_raw.log 2>&1
python /app/work/index_de.py X263b09a --fixed-c > /app/work/X263b09a/de_raw.log 2>&1
PEAK_SKIP=1 BROAD=1 python /app/work/index_de.py X1db5091 > /app/work/X1db5091/de_raw_broad.log 2>&1
