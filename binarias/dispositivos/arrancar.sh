#!/data/data/com.termux/files/usr/bin/sh
# Centinela de binarias en papel (T95H o teléfono), con Tor y avisos a Telegram. 03/11/2026.
# Cada parte arranca solo si no está viva, así que se puede llamar las veces que sea.
# Parar todo: crear el archivo PARAR en esta carpeta. Rol: archivo «rol» (caja o telefono).
D=$(cd "$(dirname "$0")" && pwd)
cd "$D" || exit 1
umask 022
termux-wake-lock 2>/dev/null
rm -f PARAR
ROL=$(cat rol 2>/dev/null || echo caja)
export BINARIAS_NPY_BASE="$D/datos/{}_um_1m_vivo.npy" AVISOS_ROL="$ROL"
# Tras un reinicio el número viejo puede ser de otro proceso (el 06/11 era Tor): se comprueba además qué proceso es.
vivo() { [ -f "$1" ] && kill -0 "$(cat "$1")" 2>/dev/null && grep -q "$2" "/proc/$(cat "$1")/cmdline" 2>/dev/null; }

# 1) Tor, solo para los avisos (Binance va directo, como permite su regla)
if ! pgrep -x tor >/dev/null 2>&1; then
  mkdir -p "$HOME/.tor-binarias" && chmod 700 "$HOME/.tor-binarias"
  tor --RunAsDaemon 1 --SocksPort 127.0.0.1:9050 --DataDirectory "$HOME/.tor-binarias" \
      --Log "notice file $HOME/.tor-binarias/tor.log" >/dev/null 2>&1
fi

# 2) Centinela, con vigía que lo relanza si se cae
if ! vivo vigia.pid binarias.py; then
  nohup sh -c 'while [ ! -f PARAR ]; do nice -n 5 python3 -I binarias.py >> salida.log 2>&1; [ -f PARAR ] && break; echo "$(date) el centinela salió; relanzo en 30 s" >> salida.log; sleep 30; done' >/dev/null 2>&1 &
  echo $! > vigia.pid
fi

# 3) Avisos a Telegram, con su vigía
if ! vivo avisos.pid avisos.py; then
  nohup sh -c 'while [ ! -f PARAR ]; do python3 -I avisos.py >> salida.log 2>&1; [ -f PARAR ] && break; sleep 30; done' >/dev/null 2>&1 &
  echo $! > avisos.pid
fi
echo "centinela: vigía $(cat vigia.pid) · avisos: $(cat avisos.pid) · rol $ROL · en $D"
