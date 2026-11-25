$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
python -m pip install -r qt/requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed' }
python -m py_compile qt/mtr.py qt/mtr_backend.py
if ($LASTEXITCODE -ne 0) { throw 'Python syntax check failed' }
foreach ($dir in @('build','publish','publish-temp','dist')) {
    if (Test-Path $dir) { Remove-Item $dir -Recurse -Force }
}
New-Item -ItemType Directory -Force build,publish,dist | Out-Null
$previousPlatform = $env:QT_QPA_PLATFORM
$env:QT_QPA_PLATFORM = 'offscreen'
try {
    python qt/mtr.py --make-icon build/mtr.ico
    if ($LASTEXITCODE -ne 0 -or !(Test-Path build/mtr.ico)) { throw 'Icon creation failed' }
    python qt/mtr.py --smoke-test
    if ($LASTEXITCODE -ne 0) { throw 'Source UI smoke test failed' }
    python -m PyInstaller --noconfirm --clean --windowed --onedir --name MTR --icon build/mtr.ico --distpath publish-temp --workpath build/work --specpath build qt/mtr.py
    if ($LASTEXITCODE -ne 0) { throw 'Qt application packaging failed' }
    Copy-Item publish-temp/MTR/* publish -Recurse -Force
    if (!(Test-Path publish/MTR.exe)) { throw 'Missing Qt executable' }
    $preview = Join-Path $PSScriptRoot 'dist\mtr-ui-preview.png'
    $p = Start-Process -FilePath (Join-Path $PSScriptRoot 'publish\MTR.exe') -ArgumentList @('--smoke-test','--screenshot',('"' + $preview + '"')) -Wait -PassThru
    if ($p.ExitCode -ne 0 -or !(Test-Path $preview)) { throw 'Packaged Qt UI smoke test failed' }
} finally {
    $env:QT_QPA_PLATFORM = $previousPlatform
}
$iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
if (!(Test-Path $iscc)) { throw 'Install Inno Setup 6 first' }
& $iscc installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer compilation failed' }
if (!(Test-Path dist/MTR-Setup.exe)) { throw 'Missing installer' }
(Get-FileHash dist/MTR-Setup.exe -Algorithm SHA256).Hash | Set-Content dist/MTR-Setup.sha256
