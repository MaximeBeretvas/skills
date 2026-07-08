#!/usr/bin/env pwsh
# Run a Docs/Plans/<folder> step-by-step: each step-N-*.md is executed by a
# fresh `claude` session, verified via its own Verify section, then the next
# step runs. Stops on the first failure (or your "no") so you can fix and resume.
#
# PowerShell 7+ port of ralph_loop.sh. Designed to consume the output of the
# YAP skill (Docs/Plans/<name>/ with context.md + step_<n>_*.md files).
#
# Usage:
#   ./ralph_loop.ps1 <plan-folder> [-From <n>] [-Model <model>] [-Effort <level>] [-Headless]
#
# Run it from inside the git repo whose plan you want to execute — the repo
# root is taken from your current directory's git toplevel.
#
# Default is supervised: each step runs as a real interactive `claude` session,
# so escalated actions prompt you instead of aborting. You exit the session
# yourself and then confirm the step succeeded.
#
# -Headless switches to fully-unattended mode: headless `claude -p` with a
# forced JSON status/summary the script parses itself.
#
# Requires: PowerShell 7+, the `claude` CLI, and `jq`.

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true, Position = 0)]
    [string]$PlanFolder,
    [int]$From = 1,
    [string]$Model = "sonnet",
    [string]$Effort = "high",
    [switch]$Headless
)

$ErrorActionPreference = "Stop"
# Don't let expected non-zero exit codes (e.g. `git diff --quiet`) throw.
$PSNativeCommandUseErrorActionPreference = $false

$ScriptDir = $PSScriptRoot
$FormatJq = Join-Path $ScriptDir "ralph_format.jq"

$RepoRoot = (& git rev-parse --show-toplevel 2>$null)
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($RepoRoot)) {
    throw "Not inside a git repository (run this from the repo whose plan you want to execute)."
}
$RepoRoot = $RepoRoot.Trim()

if ([System.IO.Path]::IsPathRooted($PlanFolder)) {
    $PlanDir = $PlanFolder
} else {
    $PlanDir = Join-Path $RepoRoot $PlanFolder
}
if (-not (Test-Path -LiteralPath $PlanDir -PathType Container)) {
    throw "Not a directory: $PlanDir"
}

$LogsDir = Join-Path $PlanDir "logs"
New-Item -ItemType Directory -Force -Path $LogsDir | Out-Null

$Schema = '{"type":"object","properties":{"status":{"enum":["success","failure"]},"summary":{"type":"string"}},"required":["status","summary"]}'
$ClaudeExtraArgs = @("--model", $Model, "--effort", $Effort)

function Invoke-ClaudeHeadless {
    param([string]$Prompt, [string]$Log)
    Push-Location $RepoRoot
    try {
        $raw = & claude -p $Prompt --permission-mode auto --output-format stream-json --verbose --json-schema $Schema @ClaudeExtraArgs
        $claudeExit = $LASTEXITCODE
    } finally {
        Pop-Location
    }
    $raw | Set-Content -Path $Log -Encoding utf8
    $raw | jq --unbuffered -r -f $FormatJq

    $lastResult = $raw | jq -c 'select(.type=="result")' | Select-Object -Last 1
    if ($claudeExit -ne 0 -or [string]::IsNullOrWhiteSpace($lastResult)) {
        Write-Host "FAILED (session error, exit $claudeExit) — see $Log"
        return $false
    }
    $verdict = $lastResult | jq -r 'if .subtype=="success" and .structured_output.status=="success" then "success" else "failure" end'
    $summary = $lastResult | jq -r '.structured_output.summary // .result // "no summary reported"'
    Write-Host "$verdict — $summary"
    return ($verdict -eq "success")
}

function Invoke-ClaudeSupervised {
    param([string]$Prompt)
    Push-Location $RepoRoot
    try {
        & claude $Prompt --permission-mode auto @ClaudeExtraArgs
    } finally {
        Pop-Location
    }
    Write-Host ""
    $ans = Read-Host "Mark this step successful and continue? [y/N]"
    return ($ans -eq "y" -or $ans -eq "Y")
}

function Invoke-Step {
    param([string]$Prompt, [string]$Log)
    if ($Headless) {
        return Invoke-ClaudeHeadless -Prompt $Prompt -Log $Log
    } else {
        return Invoke-ClaudeSupervised -Prompt $Prompt
    }
}

$stepFiles = Get-ChildItem -LiteralPath $PlanDir -File |
    Where-Object { $_.Name -match '^step[-_]\d+[-_]' } |
    Sort-Object { [int]([regex]::Match($_.Name, '^step[-_](\d+)[-_]').Groups[1].Value) }

if ($stepFiles.Count -eq 0) {
    throw "No step-*.md files found in $PlanDir"
}

Write-Host "Found $($stepFiles.Count) step(s):"
foreach ($f in $stepFiles) { Write-Host "  - $($f.Name)" }
Write-Host ""

$PlanBase = Split-Path -Leaf $PlanDir
$PlanRel = [System.IO.Path]::GetRelativePath($RepoRoot, $PlanDir)

foreach ($f in $stepFiles) {
    $base = $f.Name
    $num = [int]([regex]::Match($base, '^step[-_](\d+)[-_]').Groups[1].Value)
    if ($num -lt $From) {
        Write-Host "Skipping $base (before -From $From)"
        continue
    }

    $rel = [System.IO.Path]::GetRelativePath($RepoRoot, $f.FullName)
    $log = Join-Path $LogsDir ($f.BaseName + ".jsonl")
    $prompt = "Execute the plan step described in $rel. It links to context.md in the same folder for shared background — read that first. Carry out the step's Actions section, then run its Verification section to confirm the step actually works. Report status via the required schema: status=`"success`" only if Verification passed; otherwise `"failure`" with the reason in summary."

    Write-Host "=== Step ${num}: $base ==="
    if (-not (Invoke-Step -Prompt $prompt -Log $log)) {
        Write-Host ""
        Write-Host "Stopping — step $num failed. Fix it, then resume with:"
        Write-Host "  ./ralph_loop.ps1 `"$PlanRel`" -From $num -Model $Model -Effort $Effort"
        exit 1
    }

    & git -C $RepoRoot add -A
    & git -C $RepoRoot diff --cached --quiet
    if ($LASTEXITCODE -eq 0) {
        Write-Host "No changes to commit for step $num"
    } else {
        $slug = ($base -replace '^step[-_]\d+[-_]', '') -replace '\.md$', ''
        & git -C $RepoRoot commit -q -m "${PlanBase}: step $num - $slug"
        Write-Host "Committed step $num"
    }
    Write-Host ""
}

$contextFile = Join-Path $PlanDir "context.md"
if ((Test-Path -LiteralPath $contextFile) -and (Select-String -LiteralPath $contextFile -Pattern "End-to-end verification" -Quiet)) {
    $relContext = [System.IO.Path]::GetRelativePath($RepoRoot, $contextFile)
    $log = Join-Path $LogsDir "end-to-end-verification.jsonl"
    $prompt = "Run the `"End-to-end verification`" section from $relContext. Report status via the required schema: success only if every check in that section passes."

    Write-Host "=== Final: end-to-end verification ==="
    if (-not (Invoke-Step -Prompt $prompt -Log $log)) {
        Write-Host ""
        Write-Host "All steps succeeded, but end-to-end verification failed — see $log"
        exit 1
    }
    Write-Host ""
}

Write-Host "All steps + end-to-end verification complete."
