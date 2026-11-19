#!/bin/sh
# Instala Pulso en su Redmi por ADB y le entrega, por el cable y sin mostrarlos, la clave del bot, el chat y los puentes
# webtunnel del Tor del PC. Luego deja el Pulso del PC solo con los avisos del centinela (los demás los da el teléfono).
# Uso (Git Bash), con el teléfono conectado y la pantalla desbloqueada:  sh instalar.sh
set -e
cd "$(dirname "$0")"
ADB=/c/Users/ni109/AppData/Local/Microsoft/WinGet/Packages/Genymobile.scrcpy_Microsoft.Winget.Source_8wekyb3d8bbwe/scrcpy-win64-v4.1/adb.exe
"$ADB" get-state >/dev/null 2>&1 || { echo "No veo el teléfono por USB: conéctelo y acepte la depuración."; exit 1; }

echo "Instalando: acepte en el teléfono el aviso «Instalar vía USB»."
"$ADB" install -r salida/Pulso.apk
"$ADB" shell appops set co.nicolas.pulso RUN_ANY_IN_BACKGROUND allow
"$ADB" shell appops set co.nicolas.pulso RUN_IN_BACKGROUND allow
"$ADB" shell pm grant co.nicolas.pulso android.permission.POST_NOTIFICATIONS 2>/dev/null || true
"$ADB" shell dumpsys deviceidle whitelist +co.nicolas.pulso >/dev/null

# Las claves se leen en el momento y van directo al teléfono; nunca se imprimen.
TOKEN=$(wsl -e cat /home/rojo/.gumroad/telegram-token | tr -d '\r\n')
CHAT=$(wsl -e cat /home/rojo/.gumroad/telegram-chat | tr -d '\r\n')
PUENTES=$(wsl -e sh -c "grep '^Bridge webtunnel' /home/rojo/.carita/tor-buscador/torrc" | tr -d '\r' | awk 'BEGIN{ORS="\\\\n"} {print}')
"$ADB" shell "am broadcast -a co.nicolas.pulso.CLAVES -n co.nicolas.pulso/.Claves --es token '$TOKEN' --es chat '$CHAT' --es puentes '$PUENTES'" | grep -o 'data="[^"]*"'

"$ADB" shell am start -n co.nicolas.pulso/.Principal >/dev/null
echo "Pulso abierto en el teléfono. Si pregunta por la batería, elija «Permitir»."

# El PC queda solo con lo que únicamente él ve: las apuestas en papel del centinela.
wsl -e sh -c 'echo centinela > /home/rojo/.pulso/modo; pkill -x pulso; sleep 1; cd /home/rojo; setsid nohup /home/rojo/.pulso/bin/pulso >/dev/null 2>&1 < /dev/null & sleep 2; tail -1 /home/rojo/.pulso/registro.log'
