[CmdletBinding()]
param(
    [string]$OutputDirectory = (Join-Path $PSScriptRoot "dist"),
    [string]$SourcePath = (Join-Path $PSScriptRoot "pokopia_installer.py"),
    [string]$InstallerName = "Pokemon-Pokopia-PT-BR-Installer-v2.5.0"
)

$ErrorActionPreference = "Stop"

$buildRoot = Join-Path $env:TEMP "PokemonPokopiaPTBRInstallerBuild"
$venvPath = Join-Path $buildRoot "venv"
$pythonPath = Join-Path $venvPath "Scripts\python.exe"
$installerSource = (Resolve-Path -LiteralPath $SourcePath).Path
$outputPath = [System.IO.Path]::GetFullPath($OutputDirectory)

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python Launcher (py.exe) não encontrado. Instale Python 3.12 e tente novamente."
}

New-Item -ItemType Directory -Force -Path $buildRoot, $outputPath | Out-Null

if (-not (Test-Path -LiteralPath $pythonPath)) {
    & py -3 -m venv $venvPath
    if ($LASTEXITCODE -ne 0) {
        throw "Não foi possível criar o ambiente virtual de compilação."
    }
}

& $pythonPath -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível preparar o pip no ambiente de compilação."
}

& $pythonPath -m pip install pyinstaller
if ($LASTEXITCODE -ne 0) {
    throw "Não foi possível instalar o PyInstaller."
}

$name = $InstallerName
$workPath = Join-Path $buildRoot "work"
$specPath = Join-Path $buildRoot "spec"
New-Item -ItemType Directory -Force -Path $workPath, $specPath | Out-Null

$pyinstallerArgs = @(
    "-m", "PyInstaller",
    "--onefile",
    "--windowed",
    "--clean",
    "--noconfirm",
    "--name", $name,
    "--distpath", $outputPath,
    "--workpath", $workPath,
    "--specpath", $specPath,
    $installerSource
)
& $pythonPath @pyinstallerArgs

if ($LASTEXITCODE -ne 0) {
    throw "A compilação do instalador falhou."
}

$exePath = Join-Path $outputPath ($name + ".exe")
if (-not (Test-Path -LiteralPath $exePath)) {
    throw "A compilação terminou sem gerar o executável esperado: $exePath"
}

Write-Output $exePath
