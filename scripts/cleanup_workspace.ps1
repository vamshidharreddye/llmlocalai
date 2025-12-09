param(
    [switch]$Execute
)

# Cleanup / archive helper for the project workspace
# Usage:
#  - Dry run (default): `./scripts/cleanup_workspace.ps1`
#  - Execute changes: `./scripts/cleanup_workspace.ps1 -Execute`

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Resolve-Path (Join-Path $scriptDir '..')
$backend = Join-Path $projectRoot 'backend'
$archive = Join-Path $backend 'archive'

Write-Output "Project root: $projectRoot"
Write-Output "Backend: $backend"
Write-Output "Archive dir: $archive"

if (-not (Test-Path $archive)) {
    Write-Output "Creating archive directory: $archive"
    if ($Execute) { New-Item -ItemType Directory -Path $archive | Out-Null }
}

$filesToArchive = @('app.py','indexer.py','search.py')

foreach ($f in $filesToArchive) {
    $src = Join-Path $backend $f
    $dest = Join-Path $archive $f
    if (Test-Path $src) {
        if (-not (Test-Path $dest)) {
            Write-Output "Will move: $src -> $dest"
            if ($Execute) { Move-Item -Path $src -Destination $dest -Force; Write-Output "Moved $f to archive." }
        }
        else {
            Write-Output "$f already present in archive; skipping."
        }
    }
    else {
        Write-Output "$f not found in backend; skipping."
    }
}

# Find and optionally remove __pycache__ directories
Write-Output "Scanning for __pycache__ directories (dry run). Use -Execute to delete."
$pycDirs = Get-ChildItem -Path $projectRoot -Directory -Filter '__pycache__' -Recurse -ErrorAction SilentlyContinue
if ($pycDirs) {
    foreach ($d in $pycDirs) {
        Write-Output "Found: $($d.FullName)"
        if ($Execute) {
            Remove-Item -Path $d.FullName -Recurse -Force -ErrorAction SilentlyContinue
            Write-Output "Removed: $($d.FullName)"
        }
    }
} else {
    Write-Output "No __pycache__ directories found."
}

if (-not $Execute) { Write-Output "Dry run complete. Rerun with -Execute to apply changes." }
