<#
Add Ollama install directory to the current user's PATH environment variable.

Usage (preview):
  .\scripts\add_ollama_to_path.ps1 -WhatIf

Usage (apply):
  .\scripts\add_ollama_to_path.ps1 -Apply

Notes:
- This script uses `setx` to update the user PATH permanently. After running with `-Apply`, you must restart your PowerShell/Terminal (or log out/in) to see the change.
- `setx` truncates PATH at 1024 characters on some Windows versions; be cautious if your PATH is already very long.
#>

param(
    [switch]$Apply,
    [switch]$WhatIf
)

Write-Output "Detecting Ollama executable locations..."
# Construct candidate paths explicitly as strings to avoid parser issues
$localAppPath = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe"
$candidates = @( 'C:\Program Files\Ollama\ollama.exe', $localAppPath )

$found = $null
foreach ($p in $candidates) {
    if (Test-Path $p) { $found = $p; break }
}

if (-not $found) {
    Write-Output "No Ollama executable found in common locations. Please install Ollama or provide its path."
    exit 1
}

$dir = Split-Path -Parent $found
Write-Output "Found Ollama at: $found"
Write-Output "Directory to add to PATH: $dir"

# Check current user PATH for presence
$currentPath = [Environment]::GetEnvironmentVariable('PATH', 'User')
if ($currentPath -and $currentPath.Split(';') -contains $dir) {
    Write-Output "Directory already in user PATH. No action needed."
    exit 0
}

if ($WhatIf) {
    Write-Output "WhatIf: Would add `$dir` to user PATH via setx."
    exit 0
}

if ($Apply) {
    Write-Output "Adding to user PATH (setx). This is permanent for the current user."
    $newPath = if ($currentPath) { "$currentPath;$dir" } else { $dir }
    # Use setx to persist the PATH for the user
    Write-Output "Running: setx PATH \"$newPath\""
    setx PATH "$newPath" | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Output "Successfully updated user PATH. Restart terminals to pick up the change."
        Write-Output "You can confirm by opening a new shell and running: where.exe ollama"
        exit 0
    }
    else {
        Write-Output "Failed to update PATH (setx returned non-zero). You may need to run as Administrator or manually update PATH via System settings."
        exit 2
    }
}

Write-Output "No action taken. Use -Apply to modify PATH or -WhatIf to preview."
