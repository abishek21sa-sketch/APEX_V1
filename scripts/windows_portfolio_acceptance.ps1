$ErrorActionPreference = "Stop"
Write-Host "APEX Portfolio RC1 Acceptance"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
if (-not (Test-Path ".venv\Scripts\python.exe")) { py -3 -m venv .venv }
$python = ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -e ".[dev,service]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
& $python -m pytest -q
& $python scripts/portfolio_validation.py
Write-Host "APEX_PORTFOLIO_RC1_ACCEPTANCE=PASS"
