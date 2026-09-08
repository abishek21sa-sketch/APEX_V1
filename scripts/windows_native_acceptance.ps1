param([switch]$SkipNative)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root
if ($SkipNative -or $env:APEX_SKIP_NATIVE -eq "1") { Write-Host "APEX_NATIVE_ACCEPTANCE=SKIPPED_EXPLICITLY"; exit 0 }
function Require-Command([string]$Name) {
  if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) { throw "Required APEX toolchain command not found: $Name" }
}
Require-Command "npm"
Require-Command "cargo"
Push-Location .\frontend
try { npm ci; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; npm run check; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; npm run build; if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } } finally { Pop-Location }
& cargo test --manifest-path .\backend\Cargo.toml
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
Write-Host "APEX_NATIVE_ACCEPTANCE=PASS"
