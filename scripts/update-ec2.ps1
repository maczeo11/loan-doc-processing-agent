<#
.SYNOPSIS
    Deploys the current (or a specified) git ref to the FinScan AI production
    EC2 instance over SSH: ensures your IP is allowed through the security
    group, then runs infra/deploy.sh on the box (git checkout -> docker
    compose up --build -d -> health check, with rollback guidance built in).

.DESCRIPTION
    Run this from Windows/PowerShell (Termius itself only gives you an
    interactive shell, not a one-shot deploy command) whenever you want to
    push a new release to the live box. Safe to re-run - infra/deploy.sh
    preserves the previous release ref and fails loudly (never silently) if
    the post-deploy health check doesn't pass.

.PARAMETER Ref
    Git ref (branch, tag, or commit SHA) to deploy. Defaults to "main".

.PARAMETER KeyPath
    Path to the finscan-key.pem file. Defaults to $env:FINSCAN_SSH_KEY_PATH,
    then falls back to ~/.ssh/finscan-key.pem.

.EXAMPLE
    .\scripts\update-ec2.ps1
    Deploys the latest main.

.EXAMPLE
    .\scripts\update-ec2.ps1 -Ref v1.2.0
    Deploys a specific tag.
#>

param(
    [string]$Ref = "main",
    [string]$KeyPath = $(if ($env:FINSCAN_SSH_KEY_PATH) { $env:FINSCAN_SSH_KEY_PATH } else { "$HOME\.ssh\finscan-key.pem" }),
    [string]$Ec2Host = "13.207.15.137",
    [string]$User = "ubuntu",
    [string]$RemoteAppDir = "/opt/finscan/app"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $KeyPath)) {
    Write-Error "SSH key not found at '$KeyPath'. Pass -KeyPath, or set `$env:FINSCAN_SSH_KEY_PATH."
    exit 1
}

# 1. Make sure THIS machine's current IP is allowed through the security
#    group (college wifi vs phone 5G have different IPs - see
#    scripts/allow-my-ip.ps1 for why this has to run every time).
Write-Host "==> Ensuring SSH access for this network..." -ForegroundColor Cyan
& "$PSScriptRoot\allow-my-ip.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Error "allow-my-ip.ps1 failed - aborting deploy."
    exit 1
}

# 2. Run the existing on-box deploy script remotely. infra/deploy.sh already
#    does git fetch/checkout, docker compose up --build -d, and a 30x2s
#    health-check retry loop with rollback guidance on failure - this just
#    invokes it over SSH instead of you typing it into Termius by hand.
Write-Host "==> Deploying ref '$Ref' to $User@$Ec2Host..." -ForegroundColor Cyan
$remoteCommand = "cd $RemoteAppDir && ./infra/deploy.sh $Ref"

ssh -i $KeyPath -o StrictHostKeyChecking=accept-new "$User@$Ec2Host" $remoteCommand

if ($LASTEXITCODE -eq 0) {
    Write-Host "==> Deploy succeeded." -ForegroundColor Green
} else {
    Write-Host "==> Deploy FAILED (exit code $LASTEXITCODE). To roll back:" -ForegroundColor Red
    Write-Host "    ssh -i `"$KeyPath`" $User@$Ec2Host `"cd $RemoteAppDir && ./infra/rollback.sh`""
    exit $LASTEXITCODE
}
