#!/data/data/com.termux/files/usr/bin/sh
# Nodo puente de las binarias (17/11/2026). Arranca solo si no está vivo; se puede llamar las veces que sea.
# Parar: crear el archivo PARAR en esta carpeta. Vive aparte del centinela, del Centro y del operador: solo lee sus archivos.
D=$(cd "$(dirname "$0")" && pwd)
cd "$D" || exit 1
umask 022
P=/data/data/com.termux/files/usr
[ -d "$P/bin" ] && export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
rm -f PARAR
if ! pgrep -f "while \[ ! -f PARAR \]; do .*python3 -I nodo.py" >/dev/null 2>&1; then
  nohup sh -c 'while [ ! -f PARAR ]; do pgrep -f "^python3 -I nodo.py" >/dev/null || nice -n 5 python3 -I nodo.py >> salida.log 2>&1; [ -f PARAR ] && break; sleep 30; done' >/dev/null 2>&1 &
  echo $! > vigia.pid
fi
echo "nodo: vigía $(cat vigia.pid 2>/dev/null) en $D"
