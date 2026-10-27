# UNIR-Y-SUBIR-v4.ps1  (27/10/2026)
# Para cuando GitHub rechaza la subida con «non-fast-forward»: la rama de GitHub tiene commits que el paquete no tiene.
# Une las dos historias (git merge, sin borrar nada de ninguna) en una carpeta temporal, sin tocar tu copia de trabajo,
# y sube el resultado. Nunca fuerza la subida. Te pide autorización (S/N) antes de cada paso que toca algo.
#
# CÓMO EJECUTARLO (en Descargas, en una ventana de PowerShell):
#   cd "$env:USERPROFILE\Downloads"
#   Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned      (responde S)
#   Unblock-File .\UNIR-Y-SUBIR-v4.ps1
#   .\UNIR-Y-SUBIR-v4.ps1
param(
    [string]$Repo   = "$env:USERPROFILE\Ingresos\trader-btc",
    [string]$Bundle = "",
    [string]$Rama   = "claude/encargo-cloud-md-q0u3ex"
)
# "Continue": en Windows PowerShell 5.1, con "Stop", los mensajes normales de git por stderr pueden cortar el script.
$ErrorActionPreference = "Continue"
$Temp = Join-Path $env:TEMP "trader-btc-union"

function Paso($t)  { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Salir($t) { Write-Host ""; Write-Host $t -ForegroundColor Yellow; Read-Host "Pulsa Enter para cerrar"; exit 1 }
function Falla($t) { Write-Host ""; Write-Host "ERROR: $t" -ForegroundColor Red; Read-Host "Pulsa Enter para cerrar"; exit 1 }
function Autoriza($t) {
    do { $r = Read-Host "$t  ¿Autorizas? (S/N)" } until ($r -match '^[SsNn]$')
    if ($r -notmatch '^[Ss]$') { Salir "No autorizado: no se hizo nada más." }
}

Paso "1) Repositorio y paquete"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Falla "No encuentro git." }
if (-not (Test-Path "$Repo\.git")) { Falla "No encuentro el repositorio en $Repo. Ejecuta el script con -Repo `"<ruta de tu trader-btc>`"." }
if (-not $Bundle) {
    $carpetas = @($PSScriptRoot, "$env:USERPROFILE\Downloads", "$env:USERPROFILE\Descargas") | Where-Object { $_ -and (Test-Path $_) }
    $reciente = Get-ChildItem -Path $carpetas -Filter "consolidacion*.bundle" -File -ErrorAction SilentlyContinue |
                Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($reciente) { $Bundle = $reciente.FullName }
}
if (-not $Bundle -or -not (Test-Path $Bundle)) { Falla "No encuentro el paquete consolidacion*.bundle en Descargas." }
$Bundle = (Resolve-Path $Bundle).Path
Write-Host "Repositorio: $Repo"
Write-Host "Paquete (el más reciente): $Bundle  ($((Get-Item $Bundle).LastWriteTime))"
Set-Location $Repo

Autoriza "Traer de GitHub la rama $Rama (solo lectura) y cargar el paquete."
git fetch origin $Rama
if ($LASTEXITCODE -ne 0) { Falla "No se pudo leer de GitHub (sesión, firewall o antivirus)." }
git fetch $Bundle "${Rama}:refs/consolidacion/paquete" --force
if ($LASTEXITCODE -ne 0) { Falla "No se pudieron cargar los commits del paquete." }

Paso "2) Qué tiene cada lado"
Write-Host "Commits que SOLO están en GitHub (se conservan):" -ForegroundColor Cyan
git log --oneline "refs/consolidacion/paquete..origin/$Rama"
Write-Host ""
Write-Host "Commits que SOLO están en el paquete de Claude (se suben):" -ForegroundColor Cyan
git log --oneline "origin/$Rama..refs/consolidacion/paquete"
$soloGitHub = @(git rev-list "refs/consolidacion/paquete..origin/$Rama")
$soloPaquete = @(git rev-list "origin/$Rama..refs/consolidacion/paquete")
if ($soloPaquete.Count -eq 0) { git update-ref -d refs/consolidacion/paquete; Salir "GitHub ya tiene todo lo del paquete: no hay nada que subir." }

Paso "3) Unir las dos historias en una carpeta temporal ($Temp)"
Autoriza "Unir con git merge (sin borrar nada de ningún lado)."
if (Test-Path $Temp) { git worktree remove --force $Temp | Out-Null; if (Test-Path $Temp) { Remove-Item -Recurse -Force $Temp } }
git worktree prune
git worktree add --detach $Temp refs/consolidacion/paquete
if ($LASTEXITCODE -ne 0) { Falla "No se pudo preparar la carpeta temporal." }
Set-Location $Temp
if ($soloGitHub.Count -gt 0) {
    git merge --no-edit -m "Unir la rama de GitHub con el paquete de la sesión de Claude" "origin/$Rama"
    if ($LASTEXITCODE -ne 0) {
        Write-Host ""
        Write-Host "Hay conflicto en estos archivos:" -ForegroundColor Red
        git diff --name-only --diff-filter=U
        git merge --abort
        Set-Location $Repo
        git worktree remove --force $Temp | Out-Null
        Falla "No subí nada. Copia la lista de archivos de arriba y pásasela a Claude."
    }
}

Paso "4) Subir"
Write-Host "Se subirá esto encima de lo que ya hay en GitHub (sin borrar nada):" -ForegroundColor Cyan
git log --oneline -5
Autoriza "Subir a GitHub, rama $Rama."
git push origin "HEAD:refs/heads/$Rama"
$ok = ($LASTEXITCODE -eq 0)
Set-Location $Repo
git worktree remove --force $Temp | Out-Null
git update-ref -d refs/consolidacion/paquete
if (-not $ok) { Falla "GitHub rechazó la subida. Copia el mensaje de arriba y pásaselo a Claude." }

Paso "Comprobación final"
git fetch origin $Rama
git log --oneline -3 "origin/$Rama"
Write-Host ""
Write-Host "LISTO: todo está en GitHub, rama $Rama (lo que ya había más lo de Claude)." -ForegroundColor Green
Read-Host "Pulsa Enter para cerrar"
