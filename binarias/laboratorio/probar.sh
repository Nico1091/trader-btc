#!/data/data/com.termux/files/usr/bin/sh
# Pruebas del laboratorio en la caja (11/11/2026): candado, recorte y huella de paridad con el PC (prueba.log), y una marcha
# en seco de 30 min sin Telegram sobre una base aparte (seco.log). La marcha en seco necesita que el laboratorio no esté
# corriendo (usa su mismo puerto como candado).
D=/data/local/tmp/laboratorio
cd "$D" || exit 1
umask 000
P=/data/data/com.termux/files/usr
export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 LAB_CACHE_MB=300
{ echo "inicio $(date)"; nice -n 10 python3 -I prueba_laboratorio.py --sin-centro; echo "fin $(date) código $?"; } > prueba.log 2>&1
if [ "$1" = "--seco" ]; then
  cp -f lab.db prueba_seco.db
  { echo "inicio $(date)"; nice -n 10 python3 -I laboratorio.py --seco --minutos "${2:-30}" --base prueba_seco.db; echo "fin $(date) código $?"; } > seco.log 2>&1
fi
