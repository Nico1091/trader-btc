#!/data/data/com.termux/files/usr/bin/sh
# Lleva al equipo el nodo con la ganancia antes que el acierto y el decisor «rutina» (17/11/2026, 19:00).
# Uso por adb: run-as com.termux sh /data/local/tmp/aprobador-17-11/rutina.sh FASE [raiz]
#   FASE: probar (carpeta aparte, sin tocar lo que corre) · instalar (para, copia lo de antes, pone lo nuevo, decisor rutina,
#         arranca) · comprobar (procesos, arranque y una lectura real en GitHub) · volver (deja lo de antes y arranca)
#   raiz: carpeta con nodo/ (teléfono: la de Termux; caja: /data/local/tmp). Solo se toca el nodo.
P=/data/data/com.termux/files/usr
export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
S=/data/local/tmp/aprobador-17-11/rutina
R="${2:-$HOME}"
cd "$R" || exit 1
ARCHIVOS="nodo.py CONTEXTO-NODO.md prueba_rutina.py"

vivo() {
  pgrep -f "^python3 -I nodo.py" >/dev/null || pgrep -f "while \[ ! -f PARAR \]; do .*python3 -I nodo.py" >/dev/null
}

parar() {
  touch nodo/PARAR
  i=0
  while vivo; do
    i=$((i + 1))
    if [ "$i" -gt 50 ]; then echo "el nodo no paró en 150 s"; rm -f nodo/PARAR; exit 1; fi
    sleep 3
  done
}

arrancar() {
  setsid sh nodo/arrancar_nodo.sh < /dev/null
  sleep 8
  grep "nodo arrancó" nodo/nodo.log | tail -1
}

case "$1" in
  probar)
    Z="$TMPDIR/prueba-rutina-17-11"
    rm -rf "$Z"
    mkdir -p "$Z/nodo" "$Z/operador" || exit 1
    cp nodo/*.py nodo/*.md "$Z/nodo/"
    for f in $ARCHIVOS; do cp "$S/$f" "$Z/nodo/$f"; done
    cp "$S/aprobacion.py" "$Z/operador/aprobacion.py"
    cd "$Z/nodo" || exit 1
    echo "python: $(python3 -V 2>&1)"
    sha256sum $ARCHIVOS | cut -c1-16,65-
    for prueba in prueba_rutina.py prueba_nodo.py; do
      python3 -I "$prueba" > "$Z/$prueba.txt" 2>&1
      echo "$prueba: salida $? · $(tail -1 "$Z/$prueba.txt")"
      grep -E "^FALLO|Traceback" "$Z/$prueba.txt" | head -5
    done
    cd / && rm -rf "$Z"
    ;;
  instalar)
    parar
    for f in nodo/nodo.py nodo/CONTEXTO-NODO.md nodo/config.json; do
      [ -e "$f.antes-rutina-17-11" ] || cp -p "$f" "$f.antes-rutina-17-11"
    done
    for f in $ARCHIVOS; do cp "$S/$f" "nodo/$f" || exit 1; done
    python3 -I - <<'FIN' || exit 1
import json, os
c = json.load(open("nodo/config.json", encoding="utf-8"))
c["decisor"] = "rutina"
with open("nodo/config.json.tmp", "w", encoding="utf-8") as f:
    json.dump(c, f, ensure_ascii=False, indent=1)
os.replace("nodo/config.json.tmp", "nodo/config.json")
print("config.json: decisor =", c["decisor"], "· rutas_claude =", c.get("rutas_claude"))
FIN
    cd nodo && sha256sum $ARCHIVOS | cut -c1-16,65- && cd ..
    arrancar
    ;;
  comprobar)
    ps -A -o pid,ppid,etime,args | grep -E "python3 -I nodo\.py" | grep -v -e grep -e while
    grep "nodo arrancó" nodo/nodo.log | tail -1
    cd nodo && python3 -I -c "
import nodo as N
c = N.config()
print('decisor:', c['decisor'], '· rutina:', c['rutina_id'], '· repositorio:', c['repo_decisiones'])
print('lectura real en GitHub de la decisión de prueba de las 16:29:', N.decision_de_rutina(c, 'prueba-17-11-e4'))
"
    ;;
  volver)
    parar
    for f in nodo/nodo.py nodo/CONTEXTO-NODO.md nodo/config.json; do
      [ -e "$f.antes-rutina-17-11" ] && cp -p "$f.antes-rutina-17-11" "$f"
    done
    rm -f nodo/prueba_rutina.py
    arrancar
    ;;
  *)
    echo "uso: rutina.sh probar|instalar|comprobar|volver [raiz]"
    exit 2
    ;;
esac
