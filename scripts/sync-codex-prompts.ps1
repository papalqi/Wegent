<#
.SYNOPSIS
Sync project Codex prompts to the user's Codex home directory.

.DESCRIPTION
Copies all files under `<repo>/.codex/prompts/` into `<CODEX_HOME>/prompts/` (or `%USERPROFILE%\.codex\prompts`).
This makes `/prompts:*` commands available in the Codex CLI.
#>

[CmdletBinding(SupportsShouldProcess = $true)]
param(
  # Optional: explicit repo root (defaults to the parent of this script's directory).
  [string]$RepoRoot,

  # Optional: explicit Codex home directory (defaults to $env:CODEX_HOME, then "$HOME/.codex").
  [string]$CodexHome
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-AbsolutePath([string]$Path) {
  return (Resolve-Path -LiteralPath $Path).Path
}

if (-not $RepoRoot) {
  $RepoRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..')).Path
} else {
  $RepoRoot = Get-AbsolutePath $RepoRoot
}

$sourcePromptsDir = Join-Path (Join-Path $RepoRoot '.codex') 'prompts'
if (-not (Test-Path -LiteralPath $sourcePromptsDir -PathType Container)) {
  throw "Source prompts directory not found: $sourcePromptsDir"
}
$sourcePromptsDir = Get-AbsolutePath $sourcePromptsDir

if (-not $CodexHome) {
  if ($env:CODEX_HOME) {
    $CodexHome = $env:CODEX_HOME
  } else {
    $userHome = if ($env:USERPROFILE) { $env:USERPROFILE } else { $HOME }
    $CodexHome = Join-Path $userHome '.codex'
  }
}

if (-not (Test-Path -LiteralPath $CodexHome -PathType Container)) {
  New-Item -ItemType Directory -Force -Path $CodexHome | Out-Null
}
$CodexHome = Get-AbsolutePath $CodexHome

$destPromptsDir = Join-Path $CodexHome 'prompts'
New-Item -ItemType Directory -Force -Path $destPromptsDir | Out-Null

$files = Get-ChildItem -LiteralPath $sourcePromptsDir -File -Recurse -Force
if (-not $files -or $files.Count -eq 0) {
  Write-Warning "No prompt files found under: $sourcePromptsDir"
  exit 0
}

$copied = 0
foreach ($file in $files) {
  $relative = $file.FullName.Substring($sourcePromptsDir.Length).TrimStart('\', '/')
  $destFile = Join-Path $destPromptsDir $relative
  $destDir = Split-Path -Parent $destFile
  if (-not (Test-Path -LiteralPath $destDir -PathType Container)) {
    New-Item -ItemType Directory -Force -Path $destDir | Out-Null
  }

  if ($PSCmdlet.ShouldProcess($destFile, "Copy prompt '$relative'")) {
    Copy-Item -LiteralPath $file.FullName -Destination $destFile -Force
    $copied++
  }
}

Write-Host "Synced $copied prompt file(s) to: $destPromptsDir"
