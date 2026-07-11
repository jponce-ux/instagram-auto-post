<#====================================================================
  auto-commit.ps1 — Spec Kit Git Auto-Commit Hook (PowerShell)
  
  Usage: .specify/extensions/git/scripts/powershell/auto-commit.ps1 <event_name>
  
  Example: .specify/extensions/git/scripts/powershell/auto-commit.ps1 after_specify
  
  Reads .specify/extensions/git/git-config.yml to determine if
  auto-commit is enabled for the given event. Falls back to
  auto_commit.default if no event-specific config exists.
#===================================================================#>

param(
    [Parameter(Mandatory = $true)]
    [string]$EventName
)

# ---------- Paths ----------
$ConfigPath = Resolve-Path ".specify/extensions/git/git-config.yml" -ErrorAction SilentlyContinue
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

# ---------- Helper: Parse YAML value for a given key path ----------
function Get-YamlValue {
    param(
        [string]$ConfigPath,
        [string[]]$KeyPath
    )
    
    try {
        $lines = Get-Content -Path $ConfigPath -ErrorAction Stop
    }
    catch {
        return $null
    }
    
    $currentLevel = 0
    $currentPath = @()
    $result = $null
    
    foreach ($line in $lines) {
        # Skip empty lines and comments
        if ($line.Trim() -eq '' -or $line.TrimStart().StartsWith('#')) {
            continue
        }
        
        # Calculate indentation level (2 spaces = 1 level)
        $indent = 0
        foreach ($ch in $line.ToCharArray()) {
            if ($ch -eq ' ') { $indent++ }
            else { break }
        }
        $level = $indent / 2
        
        # Extract key and value
        if ($line -match '^\s*([\w-]+):\s*(.*)$') {
            $key = $matches[1]
            $value = $matches[2].Trim()
            
            # Adjust path based on indentation
            if ($level -le ($currentPath.Count - 1)) {
                $currentPath = $currentPath[0..($level - 1)]
            }
            
            if ($value -eq '') {
                # This key has sub-keys
                if ($level -ge $currentPath.Count) {
                    $currentPath += $key
                }
                else {
                    $currentPath[$level] = $key
                    if ($level -lt $currentPath.Count - 1) {
                        $currentPath = $currentPath[0..$level]
                    }
                }
            }
            else {
                # This key has a scalar value
                if ($level -ge $currentPath.Count) {
                    $currentPath += $key
                }
                else {
                    $currentPath[$level] = $key
                    if ($level -lt $currentPath.Count - 1) {
                        $currentPath = $currentPath[0..$level]
                    }
                }
                
                # Check if current path matches requested key path
                $matched = $true
                for ($i = 0; $i -lt $KeyPath.Length; $i++) {
                    if ($i -ge $currentPath.Count -or $currentPath[$i] -ne $KeyPath[$i]) {
                        $matched = $false
                        break
                    }
                }
                
                if ($matched) {
                    $result = $value
                }
            }
        }
    }
    
    return $result
}

# ---------- Main ----------

# 1. Check config file exists
if (-not (Test-Path ".specify/extensions/git/git-config.yml")) {
    Write-Host "  ⚠ Git config not found. Skipping auto-commit."
    exit 0
}

# 2. Check git is available
$gitCmd = Get-Command "git" -ErrorAction SilentlyContinue
if (-not $gitCmd) {
    Write-Host "  ⚠ Git is not installed or not in PATH. Skipping auto-commit."
    exit 0
}

# 3. Check we're in a git repo
$gitDir = & git rev-parse --git-dir 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ⚠ Not a git repository. Skipping auto-commit."
    exit 0
}

# 4. Determine if auto-commit is enabled for this event
$enabledStr = Get-YamlValue -ConfigPath ".specify/extensions/git/git-config.yml" -KeyPath @("auto_commit", $EventName, "enabled")
if ($null -eq $enabledStr) {
    # Fall back to default
    $enabledStr = Get-YamlValue -ConfigPath ".specify/extensions/git/git-config.yml" -KeyPath @("auto_commit", "default")
}

$enabled = ($enabledStr -eq 'true')

if (-not $enabled) {
    Write-Host "  ℹ Auto-commit disabled for '$EventName'. Skipping."
    exit 0
}

# 5. Get commit message
$commitMsg = Get-YamlValue -ConfigPath ".specify/extensions/git/git-config.yml" -KeyPath @("auto_commit", $EventName, "message")
if (-not $commitMsg) {
    $commitMsg = "[Spec Kit] Auto-commit after $EventName"
}

# 6. Check if there are changes to commit
$status = & git status --porcelain 2>&1
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($status)) {
    Write-Host "  ℹ No changes to commit after '$EventName'."
    exit 0
}

# 7. Stage and commit
Write-Host "  ✔ Auto-commit enabled for '$EventName' — committing changes..."
& git add .
& git commit -m $commitMsg

if ($LASTEXITCODE -eq 0) {
    Write-Host "  ✔ Committed: $commitMsg"
}
else {
    Write-Host "  ⚠ Git commit failed (exit code: $LASTEXITCODE)."
}

exit $LASTEXITCODE
