#!/data/data/com.termux/files/usr/bin/sh
# Prueba la rama claude/aprobador-binarias-2026-11-17 en una carpeta aparte, sin tocar lo que corre (17/11/2026).
# Uso por adb: run-as com.termux sh /data/local/tmp/aprobador-17-11/probar.sh [raiz]
#   raiz: carpeta donde viven nodo/ y operador/ en este equipo (teléfono: la de Termux; caja: /data/local/tmp).
P=/data/data/com.termux/files/usr
export PREFIX="$P" HOME=/data/data/com.termux/files/home PATH="$P/bin:$PATH" TMPDIR="$P/tmp"
S=/data/local/tmp/aprobador-17-11
R="${1:-$HOME}"
Z="$TMPDIR/prueba-aprobador-17-11"
rm -rf "$Z"
mkdir -p "$Z/nodo" "$Z/operador" "$Z/antes" || exit 1
# Código vigente, sin estados, registros ni llaves.
cp "$R"/nodo/*.py "$R"/nodo/*.md "$Z/nodo/" 2>/dev/null
if [ -d "$R/operador" ]; then
  cp "$R"/operador/*.py "$R"/operador/*.md "$Z/operador/" 2>/dev/null
  cp -r "$R/operador/datos" "$Z/operador/datos"
  cp "$R"/operador/*.py "$Z/antes/"
  cp -r "$R/operador/datos" "$Z/antes/datos"
fi
# La rama encima.
cp "$S"/nodo/* "$Z/nodo/"
cp "$S"/operador/* "$Z/operador/"
echo "python: $(python3 -V 2>&1)"
cd "$Z/nodo" || exit 1
sha256sum nodo.py CONTEXTO-NODO.md prueba_nodo.py medir_combinacion.py medir_nodo.py | cut -c1-16,65-
echo "== prueba_nodo.py"
python3 -I prueba_nodo.py > "$Z/prueba_nodo.txt" 2>&1
echo "salida $?"
grep -E "FALLO|Traceback|Error" "$Z/prueba_nodo.txt" | head -20
tail -2 "$Z/prueba_nodo.txt"
if [ -f "$Z/operador/operador.py" ]; then
  cd "$Z/operador" || exit 1
  sha256sum aprobacion.py ejecutor.py prueba_aprobacion.py simulador.py | cut -c1-16,65-
  echo "== prueba_aprobacion.py --antes (el operador que corre hoy)"
  python3 -I prueba_aprobacion.py --antes "$Z/antes" > "$Z/prueba_aprobacion.txt" 2>&1
  echo "salida $?"
  grep -E "FALLO|Traceback|Error" "$Z/prueba_aprobacion.txt" | head -20
  tail -2 "$Z/prueba_aprobacion.txt"
fi
echo "registro completo en $Z"
