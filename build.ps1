$ErrorActionPreference = 'Stop'
dotnet publish MTR.csproj -c Release -r win-x64 --self-contained true -o publish
if ($LASTEXITCODE -ne 0) { throw 'Publish failed' }
$iscc = Join-Path ${env:ProgramFiles(x86)} 'Inno Setup 6\ISCC.exe'
& $iscc installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer failed' }
if (!(Test-Path dist/MTR-Setup.exe)) { throw 'Missing installer' }
(Get-FileHash dist/MTR-Setup.exe -Algorithm SHA256).Hash | Set-Content dist/MTR-Setup.sha256
