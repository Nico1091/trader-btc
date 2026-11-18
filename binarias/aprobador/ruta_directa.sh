#!/data/data/com.termux/files/usr/bin/sh
# Orden del dueño (17/11/2026, 18:20): Claude sale directo por la IP de la casa, sin Tor, para que la IP quede siempre la misma.
# Pone "rutas_claude": ["directa"] en nodo/config.json y reinicia el nodo para que lo lea.
# Uso por adb: run-as com.termux sh /data/local/tmp/aprobador-17-11/ruta_directa.sh [raiz]
P=/data/data/com.termux/files/usr
export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
R="${1:-$HOME}"
cd "$R/nodo" || exit 1
[ -e config.json.antes-ruta-17-11 ] || cp -p config.json config.json.antes-ruta-17-11
python3 -I - <<'FIN' || exit 1
import json, os
c = json.load(open("config.json", encoding="utf-8"))
c["rutas_claude"] = ["directa"]
with open("config.json.tmp", "w", encoding="utf-8") as f:
    json.dump(c, f, ensure_ascii=False, indent=1)
os.replace("config.json.tmp", "config.json")
print("config.json: rutas_claude =", c["rutas_claude"])
FIN
touch PARAR
i=0
while pgrep -f "^python3 -I nodo.py" >/dev/null || pgrep -f "while \[ ! -f PARAR \]; do .*python3 -I nodo.py" >/dev/null; do
  i=$((i + 1))
  if [ "$i" -gt 50 ]; then echo "el nodo no paró en 150 s"; rm -f PARAR; exit 1; fi
  sleep 3
done
setsid sh arrancar_nodo.sh < /dev/null
sleep 8
grep "nodo arrancó" nodo.log | tail -1
