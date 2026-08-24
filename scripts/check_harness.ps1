# check_harness.ps1 - verify harness rules before commit
# Usage: powershell -ExecutionPolicy Bypass -File scripts/check_harness.ps1
# Prints "HARNESS OK" to allow commit; any FAIL sets exit code 1.
# NOTE: keep this file pure ASCII (PowerShell 5.1 reads BOM-less files as ANSI).
$ErrorActionPreference = "Stop"
cd (Split-Path $PSScriptRoot -Parent)   # repo root
$fail = 0

# 1) toolchain / prebuilt resources must be git-ignored
# NOTE: use $LASTEXITCODE, not `if (git ...)` - in PS 5.1 a silent (no stdout) command
# in an if-condition is treated as $false regardless of exit code.
foreach ($p in @("judge/toolchain", "frontend/public/clang")) {
  git check-ignore -q $p
  if ($LASTEXITCODE -eq 0) { "OK    $p is ignored" }
  else { "FAIL  $p is NOT ignored (see .gitignore)"; $fail++ }
}

# 2) secrets / db files must not be tracked
$bad = git ls-files | Where-Object { $_ -match '(^|/)\.env$|\.db$|\.sqlite' }
if ($bad) { "FAIL  tracked secrets/db files:"; $bad | ForEach-Object { "      $_" }; $fail++ }
else { "OK    no .env / *.db tracked" }

# 3) dependency trees must not be tracked
$bad2 = git ls-files | Where-Object { $_ -match '^node_modules/|(^|/)\.venv/|(^|/)venv/' }
if ($bad2) { "FAIL  tracked dependency trees:"; $bad2 | ForEach-Object { "      $_" }; $fail++ }
else { "OK    no node_modules / .venv tracked" }

# 4) worktree must be free of toolchain noise
$noise = git status --porcelain | Where-Object { $_ -match 'toolchain|public/clang' }
if ($noise) { "FAIL  toolchain noise in git status:"; $noise; $fail++ }
else { "OK    no toolchain noise in git status" }

if ($fail -eq 0) { "`nHARNESS OK" } else { "`nHARNESS FAIL ($fail item(s))" ; exit 1 }
