$ErrorActionPreference = "Stop"
Write-Host "APEX Enterprise Acceptance"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root
if (-not (Test-Path ".venv\Scripts\python.exe")) { py -3 -m venv .venv }
$python = ".venv\Scripts\python.exe"
& $python -m pip install --upgrade pip
& $python -m pip install -e ".[dev,service,agent]"
$env:PYTEST_DISABLE_PLUGIN_AUTOLOAD = "1"
& $python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "APEX Python regression failed" }
& $python scripts/portfolio_validation.py
if ($LASTEXITCODE -ne 0) { throw "APEX portfolio validation failed" }
& $python scripts/enterprise_operability.py
if ($LASTEXITCODE -ne 0) { throw "APEX enterprise operability failed" }
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) { throw "Rust cargo is required for APEX backend acceptance" }
Push-Location backend; cargo test --locked; if ($LASTEXITCODE -ne 0) { throw "APEX Rust tests failed" }; Pop-Location
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { throw "Node/npm is required for APEX frontend acceptance" }
Push-Location frontend; npm ci; if ($LASTEXITCODE -ne 0) { throw "APEX npm ci failed" }; npm run build; if ($LASTEXITCODE -ne 0) { throw "APEX frontend build failed" }; Pop-Location
Write-Host "APEX_ENTERPRISE_ACCEPTANCE=PASS"
