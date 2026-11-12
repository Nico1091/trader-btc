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
# 07/11: lo arrancado por Termux al encender y lo lanzado por ADB viven en contextos de Android distintos; kill -0 no cruza
# de uno a otro y duplicaba los bucles. Se busca el bucle por su línea de comando, que sí se ve desde los dos. Y cada bucle
# lanza su programa solo si no hay ya una copia corriendo: nunca dos avisadores, y si la copia cae, la relanza en 30 s.
vivo() { pgrep -f "while \[ ! -f PARAR \]; do .*python3 -I $2" >/dev/null 2>&1; }

# 1) Tor, solo para los avisos (Binance va directo, como permite su regla)
if ! pgrep -x tor >/dev/null 2>&1; then
  mkdir -p "$HOME/.tor-binarias" && chmod 700 "$HOME/.tor-binarias"
  tor --RunAsDaemon 1 --SocksPort 127.0.0.1:9050 --DataDirectory "$HOME/.tor-binarias" \
      --Log "notice file $HOME/.tor-binarias/tor.log" >/dev/null 2>&1
fi

# 2) Centinela, con vigía que lo relanza si se cae
# 11/11/2026: con ESPERA_ESTADO el centinela no arranca hasta recibir el estado del otro equipo (semaforo.json,
# avisados.json, estado.json, apuestas.jsonl, senales_vivo.jsonl); al copiarlo se borra el archivo y se vuelve a llamar
# a este guion. Así no da un SÍ que el otro equipo sabe perdido. Mientras tanto arrancan solo Tor y el laboratorio.
if [ -f ESPERA_ESTADO ]; then
  echo "$(date) ESPERA_ESTADO: el centinela espera el estado del otro equipo; arrancan solo Tor y el laboratorio" >> salida.log
else
if ! vivo vigia.pid binarias.py; then
  nohup sh -c 'while [ ! -f PARAR ]; do pgrep -f "^python3 -I binarias.py" >/dev/null || { nice -n 5 python3 -I binarias.py >> salida.log 2>&1; [ -f PARAR ] && break; echo "$(date) el centinela salió; relanzo en 30 s" >> salida.log; }; sleep 30; done' >/dev/null 2>&1 &
  echo $! > vigia.pid
fi

# 3) Avisos a Telegram, con su vigía
if ! vivo avisos.pid avisos.py; then
  nohup sh -c 'while [ ! -f PARAR ]; do pgrep -f "^python3 -I avisos.py" >/dev/null || python3 -I avisos.py >> salida.log 2>&1; [ -f PARAR ] && break; sleep 30; done' >/dev/null 2>&1 &
  echo $! > avisos.pid
fi
# 4) Centro de estrategias (07/11): las cinco en papel, página en 127.0.0.1:8797 y sus avisos a Telegram.
#    Solo donde esté instalado (hoy, el teléfono), con su vigía que lo relanza si se cae.
if [ -f centro_tel.py ] && ! vivo centro.pid centro_tel.py; then
  nohup sh -c 'while [ ! -f PARAR ]; do pgrep -f "^python3 -I centro_tel.py" >/dev/null || nice -n 5 python3 -I centro_tel.py >> salida.log 2>&1; [ -f PARAR ] && break; sleep 30; done' >/dev/null 2>&1 &
  echo $! > centro.pid
fi
fi
# 5) Laboratorio de formas (11/11/2026): solo donde esté instalado (la caja). Tiene su carpeta, su PARAR y su vigía.
[ -f /data/local/tmp/laboratorio/arrancar_lab.sh ] && sh /data/local/tmp/laboratorio/arrancar_lab.sh
echo "centinela: vigía $(cat vigia.pid) · avisos: $(cat avisos.pid) · centro: $(cat centro.pid 2>/dev/null || echo no) · rol $ROL · en $D$([ -f ESPERA_ESTADO ] && echo ' · ESPERA_ESTADO')"
