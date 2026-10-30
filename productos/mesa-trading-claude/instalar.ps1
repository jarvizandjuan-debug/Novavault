# Instalador de la Mesa de Trading para Claude Code (Windows)
# Uso: clic derecho > "Ejecutar con PowerShell", o:
#   powershell -ExecutionPolicy Bypass -File instalar.ps1
$ErrorActionPreference = "Stop"

$Origen = Split-Path -Parent $MyInvocation.MyCommand.Path
$SkillsDest = if ($env:CLAUDE_SKILLS_DIR) { $env:CLAUDE_SKILLS_DIR } else { Join-Path $HOME ".claude\skills" }
$Mesa = if ($env:MESA_TRADING_HOME) { $env:MESA_TRADING_HOME } else { Join-Path $HOME "mesa-trading" }

Write-Host "== Mesa de Trading para Claude Code - instalador =="

$PyExe = $null; $PyArgs = @()
if (Get-Command py -ErrorAction SilentlyContinue) { $PyExe = "py"; $PyArgs = @("-3") }
elseif (Get-Command python -ErrorAction SilentlyContinue) { $PyExe = "python" }
if (-not $PyExe) {
  Write-Host "Necesitas Python 3.9 o superior: https://www.python.org/downloads/ (marca 'Add python.exe to PATH')"
  exit 1
}
& $PyExe @PyArgs -c "import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)"
if ($LASTEXITCODE -ne 0) { Write-Host "Tu Python es anterior a 3.9. Instala una version nueva."; exit 1 }

New-Item -ItemType Directory -Force -Path $SkillsDest, $Mesa | Out-Null
Get-ChildItem -Directory (Join-Path $Origen "skills") | ForEach-Object {
  $dest = Join-Path $SkillsDest $_.Name
  if (Test-Path $dest) { Remove-Item -Recurse -Force $dest }
  Copy-Item -Recurse $_.FullName $dest
  Write-Host "  OK skill $($_.Name)"
}

Write-Host "Creando el entorno de Python en $Mesa\.venv (1-2 minutos)..."
& $PyExe @PyArgs -m venv (Join-Path $Mesa ".venv")
$VenvPy = Join-Path $Mesa ".venv\Scripts\python.exe"
& $VenvPy -m pip install --quiet --upgrade pip
& $VenvPy -m pip install --quiet -r (Join-Path $Origen "requirements.txt")

# Lanzador para la terminal Bash (Git Bash) que usa Claude Code en Windows
$Lanzador = "#!/usr/bin/env bash`nexec `"`$(dirname `"`$0`")/.venv/Scripts/python.exe`" `"`$@`"`n"
[IO.File]::WriteAllText((Join-Path $Mesa "py"), $Lanzador)

& $VenvPy (Join-Path $SkillsDest "configurar-mesa\scripts\configurar.py") inicializar | Out-Null
& $VenvPy (Join-Path $SkillsDest "configurar-mesa\scripts\configurar.py") verificar

Write-Host ""
Write-Host "Listo. Abre Claude Code (o reinicialo si ya estaba abierto) y escribe:"
Write-Host "  configura mi mesa de trading"
