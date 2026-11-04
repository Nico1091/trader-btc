#!/bin/sh
# Compila Pulso para el teléfono sin Gradle ni librerías: aapt2 + javac + d8 + zipalign + apksigner (igual que Recordatorios).
# Antes: el motor en Rust para arm64 (../caja-telefono.sh) y Tor del Tor Browser oficial en lib/arm64-v8a.
# Uso (Git Bash):  sh construir.sh
set -e
cd "$(dirname "$0")"
SDK=/c/Users/ni109/android-sdk
BT=$SDK/build-tools/android-15
JAR=$SDK/platforms/android-35/android.jar
FIRMA=firma/pulso.jks
VERSION=${VERSION:-1}

for f in libpulso.so libtor.so liblyrebird.so; do
  [ -f "lib/arm64-v8a/$f" ] || { echo "falta lib/arm64-v8a/$f"; exit 1; }
done
cp ../../binarias-papel/OPERATIVA.md assets/OPERATIVA.md

rm -rf obj && mkdir -p obj/clases obj/dex salida

"$BT/aapt2.exe" compile --dir res -o obj/res.zip
# --java genera R.java (el servicio usa R.drawable.icono para su aviso).
"$BT/aapt2.exe" link -o obj/base.apk -I "$JAR" --manifest AndroidManifest.xml obj/res.zip -A assets \
    --min-sdk-version 34 --target-sdk-version 35 --java obj/gen \
    --version-code "$VERSION" --version-name "1.$VERSION"

# javac 26 no acepta android.jar como sistema en modo 9+; el modo 8 con bootclasspath sí.
javac -encoding UTF-8 -source 8 -target 8 -Xlint:-options -Xlint:-deprecation -d obj/clases \
    -bootclasspath "$JAR" $(find src obj/gen -name '*.java')

"$BT/d8.bat" --release --min-api 34 --lib "$JAR" --output obj/dex $(find obj/clases -name '*.class')

cp obj/base.apk obj/sin-firmar.apk
jar -u -M -f obj/sin-firmar.apk -C obj/dex classes.dex
jar -u -M -f obj/sin-firmar.apk lib/arm64-v8a/libpulso.so lib/arm64-v8a/libtor.so lib/arm64-v8a/liblyrebird.so
"$BT/zipalign.exe" -f -p 4 obj/sin-firmar.apk obj/alineado.apk

# La firma no se puede perder: sin ella no se puede actualizar la app instalada.
if [ ! -f "$FIRMA" ]; then
  mkdir -p firma
  CLAVE=$(head -c 24 /dev/urandom | base64 | tr -d '/+=' | cut -c1-28)
  printf '%s' "$CLAVE" > firma/clave.txt
  keytool -genkeypair -keystore "$FIRMA" -alias pulso -keyalg EC -groupname secp384r1 -sigalg SHA384withECDSA \
      -validity 36500 -storepass "$CLAVE" -keypass "$CLAVE" -dname "CN=Pulso, O=Nicolas, C=CO" >/dev/null 2>&1
fi
CLAVE=$(cat firma/clave.txt)
"$BT/apksigner.bat" sign --ks "$FIRMA" --ks-key-alias pulso --ks-pass "pass:$CLAVE" \
    --v1-signing-enabled false --v2-signing-enabled true --v3-signing-enabled true \
    --out salida/Pulso.apk obj/alineado.apk
ls -la salida/Pulso.apk
