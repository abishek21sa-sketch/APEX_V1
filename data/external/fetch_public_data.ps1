$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$url = "https://www.epa.gov/system/files/other-files/2026-05/model-year-2024-fuel-economy-and-technology-data.csv"
Invoke-WebRequest -Uri $url -OutFile (Join-Path $root "epa_my2024_fuel_economy_technology.csv")
Write-Host "EXTERNAL_DATA_REFRESH=PASS"
