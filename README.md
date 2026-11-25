# MTR Antivirus · Qt edition

MTR v0.2 is a Windows 10/11 x64 endpoint-security companion. It now uses a real Qt 6 desktop interface (PySide6), packaged into a self-contained Windows application. The earlier WinForms source is retained for reference, but is not included in the new installer.

## Features
- Windows-style navigation, live protection overview, quick and full scans, searchable session detection history and settings.
- Native Windows Event Log subscription via the Windows API, with fullscreen threat alerts and a locally synthesized Alert Ready-style attention sound.
- Live Defender component and signature status, signature update requests, optional attack surface reduction policies, and tray startup.
- No MTR cloud service or file/secret uploads.

**Important:** MTR uses the installed Microsoft Defender Antivirus engine for on-access and pre-execution blocking, behavior monitoring, signatures and remediation. MTR receives events after Defender reports them; it does not itself intercept process creation. It cannot guarantee that every infostealer or zero-day is stopped. Keep Defender enabled and updated. The optional hardening policies may affect legitimate applications; audit before enabling block mode.

## Install
Download MTR-Setup.exe from a successful GitHub Actions build or its prerelease. The installer bundles Qt and Python, so users do not need to install either. Administrator access is needed for installation and explicit security policy changes. MTR runs in the tray at logon; Defender provides protection independently of the MTR dashboard. This is an unsigned experimental preview, not a certified Windows Security Center antivirus provider.

## Build
On a Windows x64 machine with Python 3.12 and Inno Setup 6 installed, run `./build.ps1` in PowerShell. The workflow installs pinned dependencies, checks Python syntax, exercises the Qt pages and alert in an offscreen smoke test, builds the application with PyInstaller, tests the packaged executable, creates the Inno Setup EXE and emits a SHA-256 checksum. A UI screenshot from the synthetic smoke test is included; it is not proof of a real Defender detection.

## Test protection
Use the Settings alert preview and the official EICAR anti-malware test file in an isolated VM, not live malware. Defender may block EICAR before it can be saved; review Windows Security for actual remediation status. The alarm is a local approximation, not an official broadcast recording. Use the sound preview privately. The offscreen smoke test does not validate the native Windows Event Log subscription or actual protection behavior.
