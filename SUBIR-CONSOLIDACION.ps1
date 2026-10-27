# SUBIR-CONSOLIDACION.ps1  (versión 2, 27/10/2026)
# Sube a GitHub los commits de la sesión de Claude (rama claude/encargo-cloud-md-q0u3ex) desde el paquete
# consolidacion-pendientes.bundle. Solo usa git. No cambia la configuración de Windows, del antivirus ni del firewall.
# Te pide autorización (S/N) antes de cada paso que toca algo.
#
# CÓMO EJECUTARLO (Windows pide permiso porque el archivo viene de internet; es normal):
#   1. Clic derecho en SUBIR-CONSOLIDACION.ps1 -> Propiedades -> marca «Desbloquear» -> Aceptar.
#   2. Abre PowerShell en la carpeta del archivo (en el Explorador: Archivo -> Abrir Windows PowerShell).
#   3. Escribe:  Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
#      (solo vale para esa ventana; PowerShell te pide confirmar: responde S)
#   4. Escribe:  .\SUBIR-CONSOLIDACION.ps1
# Si tu antivirus aun así lo bloquea, usa COMANDOS-SUBIR-A-MANO.txt: son los mismos pasos, escritos a mano.
param(
    [string]$Repo   = "$env:USERPROFILE\Ingresos\trader-btc",
    [string]$Bundle = "",
    [string]$Rama   = "claude/encargo-cloud-md-q0u3ex",
    [string]$Url    = "https://github.com/Nico1091/trader-btc.git"
)
$ErrorActionPreference = "Stop"

function Paso($t)  { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Salir($t) { Write-Host ""; Write-Host $t -ForegroundColor Yellow; Read-Host "Pulsa Enter para cerrar"; exit 1 }
function Falla($t) { Write-Host ""; Write-Host "ERROR: $t" -ForegroundColor Red; Read-Host "Pulsa Enter para cerrar"; exit 1 }
function Autoriza($t) {
    do { $r = Read-Host "$t  ¿Autorizas? (S/N)" } until ($r -match '^[SsNn]$')
    if ($r -notmatch '^[Ss]$') { Salir "No autorizado: no se hizo nada más." }
}

Write-Host "Este script va a:" -ForegroundColor Cyan
Write-Host "  1) comprobar que tienes git;"
Write-Host "  2) leer el paquete consolidacion-pendientes.bundle;"
Write-Host "  3) traer de GitHub el estado actual de la rama $Rama (git puede abrir el navegador para iniciar sesión);"
Write-Host "  4) mostrarte los commits del paquete y, si autorizas, subirlos a esa rama."
Write-Host "No toca master, no borra nada en GitHub y no cambia ninguna configuración de tu equipo."
Autoriza "Empezar."

Paso "1) Comprobando git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Falla "No encuentro git. Instálalo desde https://git-scm.com/download/win y vuelve a ejecutar." }
git --version

Paso "2) Buscando el paquete"
if (-not $Bundle) {
    $candidatos = @("$PSScriptRoot\consolidacion-pendientes.bundle",
                    "$env:USERPROFILE\Downloads\consolidacion-pendientes.bundle",
                    "$env:USERPROFILE\Descargas\consolidacion-pendientes.bundle")
    $Bundle = $candidatos | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Bundle -or -not (Test-Path $Bundle)) { Falla "No encuentro consolidacion-pendientes.bundle. Ponlo en la misma carpeta que este script o en Descargas." }
$Bundle = (Resolve-Path $Bundle).Path
Write-Host "Paquete: $Bundle"

Paso "3) Repositorio local: $Repo"
if (-not (Test-Path "$Repo\.git")) {
    if ((Test-Path $Repo) -and (Get-ChildItem $Repo -Force | Select-Object -First 1)) {
        Falla "La carpeta $Repo existe pero no es un repositorio git. Ejecuta el script con -Repo `"<ruta de tu trader-btc>`"."
    }
    Autoriza "No hay repositorio en $Repo. Voy a clonarlo desde $Url (te puede pedir iniciar sesión en GitHub)."
    git clone $Url $Repo
    if ($LASTEXITCODE -ne 0) { Falla "No se pudo clonar. Revisa tu sesión de GitHub o el firewall (git usa HTTPS, puerto 443)." }
}
Set-Location $Repo
if (-not (git remote 2>$null | Select-String -SimpleMatch "origin")) {
    Autoriza "El repositorio no tiene remoto 'origin'. Voy a añadir $Url."
    git remote add origin $Url
}
Write-Host "Remoto: $(git remote get-url origin)"

Autoriza "Traer de GitHub la rama $Rama (solo lectura)."
git fetch origin $Rama
if ($LASTEXITCODE -ne 0) {
    Falla "No se pudo leer de GitHub. Si el firewall o el antivirus preguntaron por git.exe, permite la conexión y vuelve a ejecutar. Si pide iniciar sesión, usa la cuenta Nico1091."
}

Paso "4) Verificando el paquete"
git bundle verify $Bundle
if ($LASTEXITCODE -ne 0) { Falla "El paquete no es válido o le falta su base. ¿Es el último consolidacion-pendientes.bundle que te mandó Claude?" }
git fetch $Bundle "${Rama}:refs/consolidacion/paquete" --force
if ($LASTEXITCODE -ne 0) { Falla "No se pudieron cargar los commits del paquete." }
Write-Host ""
Write-Host "Commits que se subirían:" -ForegroundColor Cyan
git log --oneline "origin/$Rama..refs/consolidacion/paquete"

Autoriza "Subir estos commits a GitHub, rama $Rama."
git push origin "refs/consolidacion/paquete:refs/heads/$Rama"
if ($LASTEXITCODE -ne 0) { Falla "GitHub rechazó la subida. Copia el mensaje de arriba y pásaselo a Claude." }

$actual = git rev-parse --abbrev-ref HEAD
if ($actual -ne $Rama) {
    git branch -f $Rama refs/consolidacion/paquete | Out-Null
    Write-Host "Tu rama local $Rama quedó igual que la de GitHub. Para ver los archivos: git checkout $Rama"
} else {
    Write-Host "Estás en la rama $Rama: para traer los cambios, escribe  git merge --ff-only refs/consolidacion/paquete" -ForegroundColor Yellow
}
git update-ref -d refs/consolidacion/paquete

Paso "Comprobación final"
git fetch origin $Rama
git log --oneline -3 "origin/$Rama"
Write-Host ""
Write-Host "LISTO: los commits están en GitHub, rama $Rama." -ForegroundColor Green
Read-Host "Pulsa Enter para cerrar"
