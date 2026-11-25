$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
$release = Invoke-RestMethod -Uri 'https://api.github.com/repos/Cisco-Talos/clamav/releases/latest' -Headers @{'User-Agent'='MTR-Windows-Build';'Accept'='application/vnd.github+json'}
$zip = @($release.assets | Where-Object { $_.name -match '\.win\.x64\.zip$' }) | Select-Object -First 1
$source = @($release.assets | Where-Object { $_.name -match '^clamav-[0-9.]+\.tar\.gz$' }) | Select-Object -First 1
if (!$zip -or !$source) { throw 'Official ClamAV x64 ZIP or matching source archive not found' }
function Get-Asset($asset, $output) {
    Invoke-WebRequest -Uri $asset.browser_download_url -OutFile $output
    $actual = (Get-FileHash $output -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($asset.digest -and $asset.digest.StartsWith('sha256:') -and $actual -ne $asset.digest.Substring(7).ToLowerInvariant()) { throw "Asset digest mismatch: $($asset.name)" }
    return $actual
}
$zipHash = Get-Asset $zip 'build\clamav.zip'
$srcHash = Get-Asset $source 'dist\clamav-source.tar.gz'
Expand-Archive -Path 'build\clamav.zip' -DestinationPath 'build\clamav-extracted' -Force
$daemon = Get-ChildItem 'build\clamav-extracted' -Filter clamd.exe -Recurse | Select-Object -First 1
if (!$daemon) { throw 'Missing clamd.exe in official archive' }
New-Item -ItemType Directory -Force 'publish\clamav' | Out-Null
Copy-Item (Join-Path $daemon.DirectoryName '*') 'publish\clamav' -Recurse -Force
foreach ($file in @('clamd.exe','freshclam.exe','clamscan.exe')) {
    if (!(Test-Path (Join-Path 'publish\clamav' $file))) { throw "Missing $file" }
}
@("ClamAV $($release.tag_name)","Binary asset: $($zip.browser_download_url)","Binary SHA256: $zipHash","Corresponding source: $($source.browser_download_url)","Source SHA256: $srcHash","ClamAV is distributed under its upstream license; see included upstream licensing files.") | Set-Content 'dist\clamav-provenance.txt'
Copy-Item 'dist\clamav-provenance.txt' 'publish\clamav\mtr-provenance.txt'
