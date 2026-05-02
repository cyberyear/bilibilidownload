Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

py -3.11 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
