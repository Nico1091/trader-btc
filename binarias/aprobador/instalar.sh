#!/data/data/com.termux/files/usr/bin/sh
# Lleva la rama claude/aprobador-binarias-2026-11-17 a un equipo, según binarias/aprobador/AVANCE.md (17/11/2026).
# Uso por adb: run-as com.termux sh /data/local/tmp/aprobador-17-11/instalar.sh FASE [raiz]
#   FASE: copiar (pasos 1 a 4: para, copia lo que corre, pone la rama y compara huellas; si no cuadran, vuelve atrás)
#         arrancar (paso 6) · comprobar (paso 7) · medir (paso 8) · volver (para, deja lo de antes y arranca)
#   raiz: carpeta con nodo/ y operador/ (teléfono: la de Termux; caja: /data/local/tmp, donde solo se toca el nodo).
# El operador de la caja sigue con PARAR: este guion nunca lo arranca ni le cambia el código.
P=/data/data/com.termux/files/usr
export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
S=/data/local/tmp/aprobador-17-11
R="${2:-$HOME}"
cd "$R" || exit 1
if [ "$R" = "$HOME" ]; then
  EQUIPO=telefono
  COPIAS="nodo/nodo.py nodo/CONTEXTO-NODO.md nodo/prueba_nodo.py operador/ejecutor.py"
  NUEVOS="operador/aprobacion.py operador/prueba_aprobacion.py nodo/medir_combinacion.py nodo/medir_nodo.py"
  ESPERADO="581538e3829064eb  operador/aprobacion.py
0b5448b9bbbea250  operador/ejecutor.py
3b7dfb28360a0110  operador/prueba_aprobacion.py
6912c5435be5f4b6  nodo/nodo.py
eb81f9ce4a688c3a  nodo/CONTEXTO-NODO.md
4d7b7176642ec21b  nodo/prueba_nodo.py
623ada75069a849c  nodo/medir_combinacion.py
9ad3761cfcb1d5ee  nodo/medir_nodo.py"
  ARCHIVOS="operador/aprobacion.py operador/ejecutor.py operador/prueba_aprobacion.py nodo/nodo.py nodo/CONTEXTO-NODO.md nodo/prueba_nodo.py nodo/medir_combinacion.py nodo/medir_nodo.py"
else
  EQUIPO=caja
  COPIAS="nodo/nodo.py nodo/CONTEXTO-NODO.md nodo/prueba_nodo.py"
  NUEVOS="nodo/medir_combinacion.py nodo/medir_nodo.py"
  ESPERADO="6912c5435be5f4b6  nodo/nodo.py
eb81f9ce4a688c3a  nodo/CONTEXTO-NODO.md
4d7b7176642ec21b  nodo/prueba_nodo.py
623ada75069a849c  nodo/medir_combinacion.py
9ad3761cfcb1d5ee  nodo/medir_nodo.py"
  ARCHIVOS="nodo/nodo.py nodo/CONTEXTO-NODO.md nodo/prueba_nodo.py nodo/medir_combinacion.py nodo/medir_nodo.py"
fi

huellas() { sha256sum $ARCHIVOS 2>/dev/null | cut -c1-16,65-; }

vivos() {
  pgrep -f "^python3 -I nodo.py" >/dev/null && return 0
  pgrep -f "while \[ ! -f PARAR \]; do .*python3 -I nodo.py" >/dev/null && return 0
  if [ "$EQUIPO" = telefono ]; then
    pgrep -f "^python3 -I operador.py" >/dev/null && return 0
    pgrep -f "while \[ ! -f PARAR \]; do .*python3 -I operador.py" >/dev/null && return 0
  fi
  return 1
}

parar() {
  touch nodo/PARAR
  [ "$EQUIPO" = telefono ] && touch operador/PARAR
  i=0
  while vivos; do
    i=$((i + 1))
    if [ "$i" -gt 50 ]; then echo "no pararon en 150 s"; return 1; fi
    sleep 3
  done
  echo "$EQUIPO: parados en unos $((i * 3)) s"
}

arrancar() {
  setsid sh nodo/arrancar_nodo.sh < /dev/null
  if [ "$EQUIPO" = telefono ]; then
    rm -f operador/PARAR && setsid sh operador/arrancar_operador.sh < /dev/null
  fi
}

volver_archivos() {
  for f in $COPIAS; do
    [ -e "$f.antes-aprobador-17-11" ] && cp -p "$f.antes-aprobador-17-11" "$f"
  done
  rm -f $NUEVOS
}

case "$1" in
  copiar)
    if ! parar; then rm -f nodo/PARAR operador/PARAR; arrancar; exit 1; fi
    for f in $COPIAS; do
      [ -e "$f.antes-aprobador-17-11" ] || cp -p "$f" "$f.antes-aprobador-17-11" || exit 1
    done
    for f in $ARCHIVOS; do cp "$S/$f" "$f" || { volver_archivos; arrancar; exit 1; }; done
    if [ "$(huellas)" != "$ESPERADO" ]; then
      echo "HUELLAS DISTINTAS: vuelvo atrás"
      huellas
      volver_archivos
      arrancar
      exit 1
    fi
    echo "$EQUIPO: huellas iguales a la rama ($(echo "$ESPERADO" | wc -l) de $(echo "$ESPERADO" | wc -l)); quedan parados hasta «arrancar»"
    ;;
  arrancar)
    arrancar
    sleep 20
    if vivos; then echo "$EQUIPO: corriendo"; else echo "$EQUIPO: NO arrancó"; exit 1; fi
    ;;
  comprobar)
    ps -A -o pid,ppid,args | grep -E "python3 -I (nodo|operador)\.py" | grep -v -e grep -e "while"
    echo "-- nodo.log"
    tail -4 nodo/nodo.log
    if [ "$EQUIPO" = telefono ]; then
      echo "-- operador.py estado"
      python3 -I operador/operador.py estado 2>&1 | tail -20
    else
      echo "-- operador de la caja: PARAR $( [ -e operador/PARAR ] && echo sigue || echo NO ESTÁ)"
    fi
    ;;
  medir)
    cd nodo && python3 -I medir_nodo.py 2>&1 | tail -25
    ;;
  volver)
    parar
    volver_archivos
    arrancar
    echo "$EQUIPO: de vuelta a lo de antes"
    ;;
  *)
    echo "uso: instalar.sh copiar|arrancar|comprobar|medir|volver [raiz]"
    exit 2
    ;;
esac
