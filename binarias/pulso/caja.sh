#!/bin/bash
# Compila Pulso BTC dentro de una caja sellada (bubblewrap): sin red, /usr en solo lectura, el código en solo lectura
# y una sola carpeta escribible (~/.pulso/bin). Mismo molde que la caja del Buscador.
#   caja.sh   -> ~/.pulso/bin/pulso
set -euo pipefail
FUENTE=/mnt/c/Users/ni109/Ingresos/pulso-btc/src
SALIDA=$HOME/.pulso/bin
mkdir -p "$SALIDA"
bwrap --unshare-all --die-with-parent --new-session \
  --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib64 /lib64 --symlink usr/bin /bin \
  --ro-bind /etc/alternatives /etc/alternatives --ro-bind /etc/ld.so.cache /etc/ld.so.cache \
  --proc /proc --dev /dev --tmpfs /tmp \
  --ro-bind "$FUENTE" /fuente --bind "$SALIDA" /salida \
  --clearenv --setenv PATH /usr/bin --setenv HOME /tmp --chdir /tmp \
  rustc --edition 2021 -C opt-level=3 -C codegen-units=1 -C strip=symbols -D warnings /fuente/main.rs -o /salida/pulso.nueva
mv "$SALIDA/pulso.nueva" "$SALIDA/pulso"
ls -la "$SALIDA/pulso"
