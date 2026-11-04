#!/bin/bash
# Compila el motor de Pulso para el teléfono (arm64, estático con musl) dentro de una caja sellada: sin red, el Rust de
# rustup y el código en solo lectura, una sola carpeta escribible. El resultado va a android/lib/arm64-v8a/libpulso.so
# (Android solo deja ejecutar programas que vengan dentro de la app como lib*.so).
#   caja-telefono.sh
set -euo pipefail
FUENTE=/mnt/c/Users/ni109/Ingresos/pulso-btc/src
SALIDA=$HOME/.pulso/telefono
TC=$HOME/.rustup/toolchains/stable-x86_64-unknown-linux-gnu
mkdir -p "$SALIDA"
bwrap --unshare-all --die-with-parent --new-session \
  --ro-bind /usr /usr --symlink usr/lib /lib --symlink usr/lib64 /lib64 --symlink usr/bin /bin \
  --ro-bind /etc/alternatives /etc/alternatives --ro-bind /etc/ld.so.cache /etc/ld.so.cache \
  --proc /proc --dev /dev --tmpfs /tmp \
  --ro-bind "$TC" /tc --ro-bind "$FUENTE" /fuente --bind "$SALIDA" /salida \
  --clearenv --setenv PATH /usr/bin --setenv HOME /tmp --chdir /tmp \
  /tc/bin/rustc --edition 2021 --target aarch64-unknown-linux-musl \
    -C opt-level=3 -C codegen-units=1 -C strip=symbols -C panic=abort -D warnings \
    -C linker=/tc/lib/rustlib/x86_64-unknown-linux-gnu/bin/rust-lld -C linker-flavor=ld.lld -C link-self-contained=yes \
    /fuente/main.rs -o /salida/pulso.nueva
mv "$SALIDA/pulso.nueva" "$SALIDA/pulso"
mkdir -p /mnt/c/Users/ni109/Ingresos/pulso-btc/android/lib/arm64-v8a
cp "$SALIDA/pulso" /mnt/c/Users/ni109/Ingresos/pulso-btc/android/lib/arm64-v8a/libpulso.so
ls -la "$SALIDA/pulso"
