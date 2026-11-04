#!/data/data/com.termux/files/usr/bin/sh
D=$(cd "$(dirname "$0")" && pwd); cd "$D" || exit 1
export BINARIAS_NPY_BASE="$D/datos/{}_um_1m_vivo.npy"
{ echo "inicio $(date)"; /system/bin/time -v python3 -I binarias.py --prueba 2>&1 || python3 -I binarias.py --prueba; echo "fin $(date)"; } > prueba.log 2>&1
