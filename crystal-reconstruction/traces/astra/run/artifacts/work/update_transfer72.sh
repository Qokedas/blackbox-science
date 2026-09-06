set -e
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
trap 'kill -CONT 45980 2>/dev/null || true' EXIT
while [[ -r /proc/50395/status ]] && ! grep -q '^State:.*Z' /proc/50395/status;do sleep 3;done
python /app/work/submit.py X263b09a /app/work/X263b09a/refined_g72.cif --check
cp -r /app/work/X14a2b08/search_transfer72 /app/work/X14a2b08/search_transfer72_oldG11
python /app/work/transfer_acm.py X263b09a X14a2b08 g72 transfer72
python /app/work/submit.py X14a2b08 /app/work/X14a2b08/search_transfer72/best.cif --check || true
