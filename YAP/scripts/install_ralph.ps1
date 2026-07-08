#!/usr/bin/env pwsh
# Copy the ralph loop (ralph_loop.ps1 + ralph_format.jq) into a project folder
# so it lives with the project instead of the global skills dir.
#
# Usage:
#   ./install_ralph.ps1 [target-dir]     # default target: ./scripts
#
# Run it from your project root, or pass an explicit target directory.

[CmdletBinding()]
param(
    [string]$Target = "./scripts"
)

$ErrorActionPreference = "Stop"
$SrcDir = $PSScriptRoot

New-Item -ItemType Directory -Force -Path $Target | Out-Null
Copy-Item -Path (Join-Path $SrcDir "ralph_loop.ps1") -Destination $Target -Force
Copy-Item -Path (Join-Path $SrcDir "ralph_format.jq") -Destination $Target -Force

Write-Host "Installed ralph loop into $Target/"
Write-Host "Run it from this repo with:  ./$Target/ralph_loop.ps1 Docs/Plans/<name>"
