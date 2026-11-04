@echo off
rem Pulso BTC: registra la tarea que lo arranca al iniciar sesion (oculto, dentro de WSL, todo por Tor).
rem Para quitarlo: schtasks /Delete /TN "Pulso BTC - avisos de voz" /F
powershell -NoProfile -Command "$a=New-ScheduledTaskAction -Execute 'C:\Windows\System32\conhost.exe' -Argument '--headless C:\Windows\System32\wsl.exe -d Ubuntu-26.04 -u rojo -e /home/rojo/.pulso/bin/pulso'; $t=New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME; $s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable; Register-ScheduledTask -TaskName 'Pulso BTC - avisos de voz' -Action $a -Trigger $t -Settings $s -Description 'Avisos de voz del Bitcoin a su Telegram, por Tor' -Force | Out-Null; 'Listo: Pulso BTC arrancara solo al iniciar sesion.'"
pause
