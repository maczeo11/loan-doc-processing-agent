<#
.SYNOPSIS
    FinScan AI — Local Demo Launcher
.DESCRIPTION
    Starts PostgreSQL + Redis in Docker (nothing else runs in Docker), runs
    migrations, launches the outbox dispatcher/worker/React UI as background
    jobs, then runs the FastAPI backend directly in this terminal
    (foreground, live-reload) so its logs and tracebacks stream immediately.
    Press Ctrl+C to stop the API and tear everything else down with it.
.NOTES
    Prerequisites:
      - Docker Desktop running
      - Python venv activated with all requirements installed
      - Node.js installed (for React UI)
#>

param(
    [switch]$SkipUI,        # Skip launching the React dev server
    [switch]$SkipWorker,    # Skip launching the worker (useful for API-only testing)
    [switch]$NoBrowser      # Don't auto-open browser
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)

Write-Host "`n=== FinScan AI — Local Demo ===" -ForegroundColor Cyan
Write-Host "Project root: $ProjectRoot" -ForegroundColor DarkGray

# ------------------------------------------------------------------
# Step 1: Copy .env.local → .env (if .env doesn't exist)
# ------------------------------------------------------------------
$envFile = Join-Path $ProjectRoot ".env"
$envLocal = Join-Path $ProjectRoot ".env.local"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envLocal) {
        Copy-Item $envLocal $envFile
        Write-Host "[env] Copied .env.local -> .env" -ForegroundColor Green
    } else {
        Write-Host "[env] WARNING: No .env or .env.local found. Using defaults." -ForegroundColor Yellow
    }
} else {
    Write-Host "[env] Using existing .env" -ForegroundColor DarkGray
}

# ------------------------------------------------------------------
# Step 2: Start Docker infra (PG + Redis)
# ------------------------------------------------------------------
Write-Host "`n[1/6] Starting PostgreSQL + Redis in Docker..." -ForegroundColor Yellow
docker compose -f "$ProjectRoot\infra\docker-compose.local.yml" up -d

# Wait for PG to become healthy
Write-Host "[2/6] Waiting for PostgreSQL to be healthy..." -ForegroundColor Yellow
$maxRetries = 30
for ($i = 0; $i -lt $maxRetries; $i++) {
    $result = docker exec finscan-db pg_isready -U postgres -d finscan 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "       PostgreSQL is ready!" -ForegroundColor Green
        break
    }
    Start-Sleep -Seconds 1
}
if ($i -eq $maxRetries) {
    Write-Host "ERROR: PostgreSQL did not become healthy in 30s" -ForegroundColor Red
    exit 1
}

# ------------------------------------------------------------------
# Step 3: Run Alembic migrations
# ------------------------------------------------------------------
Write-Host "[3/6] Running Alembic migrations..." -ForegroundColor Yellow
Push-Location $ProjectRoot
try {
    alembic upgrade head
    Write-Host "       Migrations complete!" -ForegroundColor Green
} catch {
    Write-Host "WARNING: Alembic migration failed (may already be up-to-date): $_" -ForegroundColor Yellow
}
Pop-Location

# ------------------------------------------------------------------
# Step 4: Create storage directory
# ------------------------------------------------------------------
$storageDir = Join-Path $ProjectRoot "data\storage"
if (-not (Test-Path $storageDir)) {
    New-Item -ItemType Directory -Path $storageDir -Force | Out-Null
    Write-Host "[prep] Created data/storage directory" -ForegroundColor Green
}

# ------------------------------------------------------------------
# Step 5: Launch supporting native processes as background jobs.
# The API itself is deliberately NOT one of these (see Step 6) - only
# Postgres/Redis run in Docker; the backend runs directly in this
# terminal so its logs/reload output/tracebacks are immediate, not
# buffered behind a job's Receive-Job poll.
# ------------------------------------------------------------------
$jobs = @()

# Outbox Dispatcher
Write-Host "[4/6] Starting Outbox Dispatcher..." -ForegroundColor Yellow
$jobs += Start-Job -Name "finscan-outbox" -ScriptBlock {
    Set-Location $using:ProjectRoot
    python -m apps.api.outbox_dispatcher
}

# Worker (ML inference)
if (-not $SkipWorker) {
    Write-Host "[5/6] Starting Worker (ML inference pipeline)..." -ForegroundColor Yellow
    $jobs += Start-Job -Name "finscan-worker" -ScriptBlock {
        Set-Location $using:ProjectRoot
        python -m worker.main
    }
} else {
    Write-Host "[5/6] Skipping worker (--SkipWorker flag)" -ForegroundColor DarkGray
}

# React UI
if (-not $SkipUI) {
    Write-Host "[6/6] Starting React UI dev server (port 3000)..." -ForegroundColor Yellow
    $jobs += Start-Job -Name "finscan-ui" -ScriptBlock {
        Set-Location (Join-Path $using:ProjectRoot "apps\ui")
        npm run dev
    }
}

# ------------------------------------------------------------------
# Print dashboard
# ------------------------------------------------------------------
Start-Sleep -Seconds 3
foreach ($job in $jobs) {
    Receive-Job -Job $job -ErrorAction SilentlyContinue
}
Write-Host "`n" -NoNewline
Write-Host "╔══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║           FinScan AI — Local Demo Running               ║" -ForegroundColor Cyan
Write-Host "╠══════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  API Server:     http://localhost:8000  (this terminal) ║" -ForegroundColor White
Write-Host "║  API Docs:       http://localhost:8000/docs             ║" -ForegroundColor White
Write-Host "║  React UI:       http://localhost:3000                  ║" -ForegroundColor White
Write-Host "║  PostgreSQL:     localhost:5432  (finscan, in Docker)   ║" -ForegroundColor DarkGray
Write-Host "║  Redis:          localhost:6379  (in Docker)            ║" -ForegroundColor DarkGray
Write-Host "╠══════════════════════════════════════════════════════════╣" -ForegroundColor Cyan
Write-Host "║  Press Ctrl+C to stop all services                     ║" -ForegroundColor Yellow
Write-Host "╚══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan

if (-not $NoBrowser) {
    Start-Process "http://localhost:3000"
}

# ------------------------------------------------------------------
# Step 6: Run the API server directly in THIS process (foreground,
# blocking, live-reload). Ctrl+C here stops uvicorn, which drops into
# the `finally` block below to clean up the background jobs and the
# Docker DB/Redis containers - so Ctrl+C still tears down everything,
# same as before, just with the backend's own logs streaming live
# instead of hidden inside a job.
# ------------------------------------------------------------------
try {
    Write-Host "`nStarting FastAPI API server directly (Ctrl+C to stop everything)...`n" -ForegroundColor DarkGray
    Push-Location $ProjectRoot
    try {
        uvicorn apps.api.main:app --host 0.0.0.0 --port 8000 --reload
    } finally {
        Pop-Location
    }
} finally {
    Write-Host "`n`nShutting down..." -ForegroundColor Yellow

    # Stop all PowerShell jobs (outbox/worker/UI)
    foreach ($job in $jobs) {
        Write-Host "  Stopping $($job.Name)..." -ForegroundColor DarkGray
        Stop-Job -Job $job -ErrorAction SilentlyContinue
        Remove-Job -Job $job -Force -ErrorAction SilentlyContinue
    }

    # Stop Docker containers (db + redis only)
    Write-Host "  Stopping Docker containers..." -ForegroundColor DarkGray
    docker compose -f "$ProjectRoot\infra\docker-compose.local.yml" down

    Write-Host "`nAll services stopped. Goodbye!" -ForegroundColor Green
}
