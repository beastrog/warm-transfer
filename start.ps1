param(
  [string]$BackendHost = "127.0.0.1",
  [int]$BackendPort = 8000
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$backend = Join-Path $root "backend"
$frontend = Join-Path $root "frontend"

# Start Backend in a new PowerShell window
$backendCmd = @(
  "cd `"$backend`"",
  "if (-not (Test-Path .venv)) { python -m venv .venv }",
  ". .venv\\Scripts\\Activate.ps1",
  "pip install -r requirements.txt",
  "uvicorn main:app --host $BackendHost --port $BackendPort --reload"
) -join "; "

Start-Process powershell -ArgumentList "-NoExit","-Command", $backendCmd | Out-Null

# Start Frontend in a new PowerShell window
$frontendCmd = @(
  "cd `"$frontend`"",
  "npm install",
  "npm run dev"
) -join "; "

Start-Process powershell -ArgumentList "-NoExit","-Command", $frontendCmd | Out-Null

Write-Host "Launched backend on http://${BackendHost}:${BackendPort} and frontend on http://localhost:3000 in separate terminals."
