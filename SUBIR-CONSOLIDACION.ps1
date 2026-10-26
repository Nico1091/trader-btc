# SUBIR-CONSOLIDACION.ps1
# Sube a GitHub los commits de la sesión de Claude en la nube (rama claude/encargo-cloud-md-q0u3ex).
# Uso: deja este archivo y consolidacion-pendientes.bundle en Descargas y haz doble clic en SUBIR CONSOLIDACION.cmd
# (o ejecuta: powershell -ExecutionPolicy Bypass -File .\SUBIR-CONSOLIDACION.ps1)
param(
    [string]$Repo   = "$env:USERPROFILE\Ingresos\trader-btc",
    [string]$Bundle = "",
    [string]$Rama   = "claude/encargo-cloud-md-q0u3ex",
    [string]$Url    = "https://github.com/Nico1091/trader-btc.git"
)
$ErrorActionPreference = "Stop"
function Paso($t) { Write-Host ""; Write-Host "==> $t" -ForegroundColor Cyan }
function Falla($t) { Write-Host ""; Write-Host "ERROR: $t" -ForegroundColor Red; Read-Host "Pulsa Enter para salir"; exit 1 }

Paso "Comprobando git"
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { Falla "No encuentro git. Instálalo desde https://git-scm.com/download/win y vuelve a ejecutar." }
git --version

Paso "Buscando el paquete consolidacion-pendientes.bundle"
if (-not $Bundle) {
    $candidatos = @("$PSScriptRoot\consolidacion-pendientes.bundle", "$env:USERPROFILE\Downloads\consolidacion-pendientes.bundle", "$env:USERPROFILE\Descargas\consolidacion-pendientes.bundle")
    $Bundle = $candidatos | Where-Object { Test-Path $_ } | Select-Object -First 1
}
if (-not $Bundle -or -not (Test-Path $Bundle)) { Falla "No encuentro consolidacion-pendientes.bundle. Ponlo en la misma carpeta que este script o en Descargas." }
$Bundle = (Resolve-Path $Bundle).Path
Write-Host "Paquete: $Bundle"

Paso "Preparando el repositorio local en $Repo"
if (-not (Test-Path "$Repo\.git")) {
    if ((Test-Path $Repo) -and (Get-ChildItem $Repo -Force | Select-Object -First 1)) {
        Falla "La carpeta $Repo existe pero no es un repositorio git. Ejecuta el script con -Repo <otra carpeta>."
    }
    Write-Host "No hay repositorio ahí: lo clono de GitHub (te puede pedir iniciar sesión)."
    git clone $Url $Repo
    if ($LASTEXITCODE -ne 0) { Falla "No se pudo clonar $Url. Revisa tu sesión de GitHub." }
}
Set-Location $Repo
$origen = git remote get-url origin 2>$null
if (-not $origen) {
    Write-Host "El repositorio no tiene remoto 'origin': lo añado ($Url)."
    git remote add origin $Url
}
Write-Host "Remoto: $(git remote get-url origin)"

Paso "Trayendo de GitHub lo que ya está subido (la base del paquete)"
git fetch origin $Rama master
if ($LASTEXITCODE -ne 0) { Falla "No se pudo leer de GitHub. Revisa tu sesión (git te abrirá el navegador para iniciar sesión)." }

Paso "Verificando el paquete"
git bundle verify $Bundle
if ($LASTEXITCODE -ne 0) { Falla "El paquete no es válido o le falta la base. ¿Es el último consolidacion-pendientes.bundle?" }

Paso "Cargando los commits del paquete"
git fetch $Bundle "${Rama}:refs/consolidacion/paquete" --force
if ($LASTEXITCODE -ne 0) { Falla "No se pudieron cargar los commits del paquete." }
Write-Host "Commits que se van a subir:"
git log --oneline "origin/$Rama..refs/consolidacion/paquete"

Paso "Subiendo a GitHub (rama $Rama)"
git push origin "refs/consolidacion/paquete:refs/heads/$Rama"
if ($LASTEXITCODE -ne 0) { Falla "GitHub rechazó la subida. Si dice 'rejected' o 'non-fast-forward', alguien subió otra cosa a la rama: avísale a Claude." }

Paso "Actualizando tu copia local de la rama"
$actual = git rev-parse --abbrev-ref HEAD
if ($actual -eq $Rama) {
    $cambios = git status --porcelain
    if ($cambios) {
        Write-Host "Estás en la rama $Rama con cambios sin guardar: no la toco. Después ejecuta: git merge --ff-only refs/consolidacion/paquete" -ForegroundColor Yellow
    } else {
        git merge --ff-only refs/consolidacion/paquete
    }
} else {
    git branch -f $Rama refs/consolidacion/paquete
    Write-Host "Rama local $Rama actualizada. Para ver los archivos: git checkout $Rama"
}
git update-ref -d refs/consolidacion/paquete

Paso "Comprobación final"
git fetch origin $Rama
git log --oneline -5 "origin/$Rama"
Write-Host ""
Write-Host "LISTO: los commits están en GitHub, en la rama $Rama." -ForegroundColor Green
Write-Host "Si quieres llevarlos a master, abre un pull request en https://github.com/Nico1091/trader-btc/compare/master...$Rama"
Read-Host "Pulsa Enter para cerrar"
