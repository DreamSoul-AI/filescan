param(
  [switch]$NoInstall,
  [string]$DistPath = "dist",
  [string]$PackageName = "filescan"
)

$ErrorActionPreference = "Stop"
$PkgDir = Join-Path "src" $PackageName
$StageFiles = @("README.md", "README_zh.md", "LICENSE", "requirements.txt")
$Staged = @()

if (-not (Test-Path $PkgDir)) { throw "Package dir not found: $PkgDir" }

Write-Host "📦 Building $PackageName from pyproject.toml"
New-Item -ItemType Directory -Force -Path $DistPath | Out-Null

Write-Host "🧩 Staging package data into $PkgDir"
foreach ($f in $StageFiles) {
  if (Test-Path $f) {
    $dest = Join-Path $PkgDir $f
    Copy-Item $f $dest -Force
    $Staged += $dest
  }
}

function Cleanup {
  Write-Host "🧹 Cleaning up staged files"
  foreach ($p in $Staged) { Remove-Item $p -Force -ErrorAction SilentlyContinue }
}

try {
  Remove-Item -Recurse -Force build, $DistPath, "*.egg-info", "src\*.egg-info" -ErrorAction SilentlyContinue

  Write-Host "🔎 Environment sanity check"
  python -c "import sys; print('sys.executable =', sys.executable); print('sys.prefix     =', sys.prefix)"
  python -m pip -V

  Write-Host "🔧 Building wheel..."
  python -m build --wheel --outdir $DistPath

  $whl = Get-ChildItem -Path $DistPath -Filter "*.whl" | Select-Object -First 1
  if (-not $whl) { throw "No wheel found in $DistPath" }
  Write-Host "✅ Built wheel: $($whl.Name)"

  if (-not $NoInstall) {
    Write-Host "📥 Installing into active Python..."
    python -m pip uninstall -y $PackageName | Out-Null
    python -m pip install $whl.FullName
  }

  Write-Host "🎉 Done."
}
finally {
  Cleanup
}