#!/data/data/com.termux/files/usr/bin/sh
# Autorizado por Nicolás el 03/11/2026: el centinela arranca solo al encender (Termux:Boot).
# Quitar: borrar ~/.termux/boot/20-centinela.sh
D=$(cd "$(dirname "$0")" && pwd)
mkdir -p "$HOME/.termux/boot"
printf '#!/data/data/com.termux/files/usr/bin/sh\n# Centinela de binarias en papel (03/11/2026)\nsleep 30\ntermux-wake-lock\n/data/data/com.termux/files/usr/bin/sh %s/arrancar.sh\n' "$D" > "$HOME/.termux/boot/20-centinela.sh"
chmod 700 "$HOME/.termux/boot/20-centinela.sh"
{ echo "arranque puesto $(date)"; echo "== activos:"; ls -la "$HOME/.termux/boot/"; cat "$HOME/.termux/boot/20-centinela.sh"; echo "== desactivados:"; ls "$HOME/.termux/boot-desactivados/" 2>/dev/null; } > "$D/arranque.log" 2>&1
