Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

py -3.11 -m pip install pyinstaller

$staticSource = Join-Path $root 'static'
$staticSpec = "$staticSource;static"

py -3.11 -m PyInstaller `
  --noconfirm `
  --clean `
  --onefile `
  --windowed `
  --name BilibiliDownloader `
  --add-data $staticSpec `
  desktop_launcher.py
