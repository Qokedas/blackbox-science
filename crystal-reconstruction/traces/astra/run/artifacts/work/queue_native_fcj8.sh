set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 PEAK_FILE=peaks_fcjsel.json NPEAK=20 NSPUR=1 TTHERR=.025 MAXERR=.045 LMAX=50 LMAX_TRI=40 INDEX_SCORE=60 INDEX_DEPTH=7
while [[ -r /proc/43632/status ]] && ! grep -q '^State:.*Z' /proc/43632/status;do sleep 5;done
for kind in 'ORTHOROMBIC P 2000 4100' 'MONOCLINIC P 1000 2100' 'MONOCLINIC P 2100 3800' 'MONOCLINIC C 2100 7000' 'TRICLINIC P 600 1650';do
 read -r sys cen vmin vmax <<< "$kind"
 INDEX_TAG=fcj timeout 260 python /app/work/index_native_fcj.py X8a6f5a8 "$sys" "$cen" 3 "$vmin" "$vmax" > /app/work/X8a6f5a8/native_fcj_${sys}_${cen}_${vmin}.log 2>&1 || true
done
