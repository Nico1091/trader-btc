#!/data/data/com.termux/files/usr/bin/sh
# Arranque del operador de Fable 5.2 en la caja (17/11/2026, sin cambiar su código). Paso 9 de PLAN-AUTOMATICO.md.
# Sin llave queda en su estado 1: solo mide con velas públicas; no compra. Parar: crear PARAR en esta carpeta.
D=$(cd "$(dirname "$0")" && pwd)
cd "$D" || exit 1
umask 022
P=/data/data/com.termux/files/usr
[ -d "$P/bin" ] && export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
if ! pgrep -f "while \[ ! -f PARAR \]; do .*python3 -I operador.py" >/dev/null 2>&1; then
  nohup sh -c 'while [ ! -f PARAR ]; do pgrep -f "^python3 -I operador.py" >/dev/null || nice -n 5 python3 -I operador.py >> salida.log 2>&1; [ -f PARAR ] && break; sleep 30; done' >/dev/null 2>&1 &
  echo $! > vigia.pid
fi
echo "operador: vigía $(cat vigia.pid 2>/dev/null) en $D"
