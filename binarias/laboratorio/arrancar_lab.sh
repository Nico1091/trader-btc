#!/data/data/com.termux/files/usr/bin/sh
# Laboratorio de binarias en papel (11/11/2026). Arranca con su vigía si no está vivo; se puede llamar las veces que sea.
# Lo llama centinela/arrancar.sh al encender (Termux:Boot) y también se puede lanzar a mano o por run-as com.termux.
# Parar: crear el archivo PARAR en esta carpeta (el ciclo sale solo y el vigía no lo relanza). Nada de esto apuesta.
D=/data/local/tmp/laboratorio
cd "$D" || exit 1
umask 000
P=/data/data/com.termux/files/usr
export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 LAB_CACHE_MB=300
rm -f PARAR
# El bucle se busca por su línea de comando: lo arrancado al encender y lo lanzado por ADB viven en contextos distintos.
if ! pgrep -f "while \[ ! -f PARAR \]; do .*laboratorio.py" >/dev/null 2>&1; then
  nohup sh -c 'while [ ! -f PARAR ]; do pgrep -f "^python3 -I laboratorio.py" >/dev/null || nice -n 10 python3 -I laboratorio.py >> salida.log 2>&1; [ -f PARAR ] && break; sleep 30; done' >/dev/null 2>&1 &
  echo "laboratorio: vigía $! en $D"
else
  echo "laboratorio: ya corría"
fi
