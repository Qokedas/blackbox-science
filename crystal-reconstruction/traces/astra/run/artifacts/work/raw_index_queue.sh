export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_raw.json NPEAK=18 NSPUR=1 INDEX_SCORE=55 INDEX_DEPTH=6 LMAX=80
while [[ -r /proc/3434/status ]] && ! grep -q '^State:.*Z' /proc/3434/status; do sleep 5; done
for id in X1db5091 Xebbd488 X8a6f5a8 X7e382cb Xb7088cf Xedd9c7b; do
 case "$id" in
  X7e382cb) vol='250 1800';export TTHERR=.016 TTHSHIFT=-.02 NPEAK=13;;
  Xb7088cf) vol='700 3200';export TTHERR=.016 TTHSHIFT=-.04 NPEAK=18;;
  Xedd9c7b) vol='400 2600';export TTHERR=.03 TTHSHIFT=0 NPEAK=18;;
  X1db5091) vol='1050 1800';export TTHERR=.03 TTHSHIFT=0 NPEAK=18;;
  Xebbd488) vol='1200 6500';export TTHERR=.03 TTHSHIFT=0 NPEAK=18;;
  X8a6f5a8) vol='1000 5500';export TTHERR=.03 TTHSHIFT=0 NPEAK=18;;
 esac
 for system in ORTHOROMBIC MONOCLINIC; do
  for center in P C; do
   timeout 150 python /app/work/index_one.py $id $system $center 4 $vol > /app/work/$id/index_raw_${system}_${center}.log 2>&1
  done
 done
 if [[ "$id" == X1db5091 || "$id" == Xedd9c7b || "$id" == X7e382cb || "$id" == Xb7088cf ]]; then
  timeout 420 python /app/work/index_one.py $id TRICLINIC P 4 $vol > /app/work/$id/index_raw_TRICLINIC_P.log 2>&1
 fi
done
