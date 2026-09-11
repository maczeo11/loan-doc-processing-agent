<#
.SYNOPSIS
    Restricts SSH (port 22) on the FinScan production security group to
    whatever public IP this script is run from, revoking any previous
    IP it had allowed.

.DESCRIPTION
    Run this before connecting with Termius whenever you switch networks
    (college wifi, phone 5G/hotspot, home, etc.) - each has a different
    public IP, and the security group only trusts one at a time. This
    swaps the old allowed IP for the current one in a single pass, so SSH
    is never left open to 0.0.0.0/0 and you're never locked out by a
    stale rule either.

.NOTES
    Requires the AWS CLI configured with the "finscan" profile.
    Verify with: aws sts get-caller-identity --profile finscan
#>

param(
    [string]$Profile = "finscan",
    [string]$Region = "ap-south-1",
    [string]$SecurityGroupId = "sg-04d3765e679802f69",
    [string]$RuleDescription = "admin-termius"
)

$ErrorActionPreference = "Stop"

Write-Host "Detecting current public IP..."
$currentIp = (Invoke-WebRequest -Uri "https://checkip.amazonaws.com" -UseBasicParsing -TimeoutSec 8).Content.Trim()
$currentCidr = "$currentIp/32"
Write-Host "Current public IP: $currentIp"

$existingRulesJson = aws ec2 describe-security-group-rules `
    --profile $Profile --region $Region `
    --filters "Name=group-id,Values=$SecurityGroupId" `
    --output json

$portRules = ($existingRulesJson | ConvertFrom-Json).SecurityGroupRules | Where-Object {
    -not $_.IsEgress -and
    $_.IpProtocol -eq "tcp" -and
    $_.FromPort -eq 22 -and
    $_.ToPort -eq 22 -and
    $_.Description -eq $RuleDescription
}

if ($portRules | Where-Object { $_.CidrIpv4 -eq $currentCidr }) {
    Write-Host "SSH is already allowed from $currentCidr. Nothing to do."
    exit 0
}

foreach ($rule in $portRules) {
    Write-Host "Revoking stale rule for $($rule.CidrIpv4)..."
    aws ec2 revoke-security-group-ingress `
        --profile $Profile --region $Region `
        --group-id $SecurityGroupId `
        --security-group-rule-ids $rule.SecurityGroupRuleId | Out-Null
}

Write-Host "Authorizing SSH from $currentCidr..."
aws ec2 authorize-security-group-ingress `
    --profile $Profile --region $Region `
    --group-id $SecurityGroupId `
    --ip-permissions "IpProtocol=tcp,FromPort=22,ToPort=22,IpRanges=[{CidrIp=$currentCidr,Description=$RuleDescription}]" | Out-Null

Write-Host "Done. SSH (port 22) on $SecurityGroupId is now allowed only from $currentCidr."
