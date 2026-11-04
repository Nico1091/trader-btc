#!/data/data/com.termux/files/usr/bin/sh
# Instala Tor (autorizado el 03/11/2026), guarda la clave del bot en privado y arranca avisos.
D=$(cd "$(dirname "$0")" && pwd)
L="$D/instalar_avisos.log"
{
echo "inicio $(date)"
export DEBIAN_FRONTEND=noninteractive
command -v tor >/dev/null 2>&1 || { yes | pkg install -y -o Dpkg::Options::=--force-confold tor 2>&1 | tail -4; }
echo "tor: $(command -v tor) $(tor --version 2>/dev/null | head -1)"
if [ -s "$D/.tg_llegada" ]; then
  mkdir -p "$HOME/.config/binarias" && chmod 700 "$HOME/.config/binarias"
  cat "$D/.tg_llegada" > "$HOME/.config/binarias/telegram" && chmod 600 "$HOME/.config/binarias/telegram"
  rm -f "$D/.tg_llegada"
fi
echo "clave guardada: $( [ -s "$HOME/.config/binarias/telegram" ] && echo sí || echo NO ) · líneas $(wc -l < "$HOME/.config/binarias/telegram" 2>/dev/null)"
sh "$D/arrancar.sh"
echo "fin $(date)"
} > "$L" 2>&1
