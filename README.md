# MTR Antivirus

MTR is a Windows 10/11 x64 endpoint-security companion with a native desktop dashboard, real-time Microsoft Defender event monitoring, fullscreen threat alerts, and optional attack-surface-reduction hardening.

**Important:** MTR uses the installed Microsoft Defender Antivirus engine for on-access and pre-execution blocking, cloud reputation, signatures and remediation. It is not a replacement kernel-mode antivirus and cannot guarantee that every infostealer or zero-day is stopped. Keep Defender enabled and up to date. The optional hardening policies can affect legitimate applications; review and apply them explicitly.

## Install
Download MTR-Setup.exe from the Windows build artifact in Actions (or the latest release when available). Administrator access is needed to install the app and change protection settings. The dashboard runs at logon, while Defender protects the machine before logon and independently of MTR.

## Build
The Windows GitHub Actions workflow builds the WinForms program and the Inno Setup executable installer. On a Windows machine with .NET SDK 8 and Inno Setup 6, run `build.ps1` from PowerShell.

## Privacy
MTR reads local Defender health and threat logs. It does not upload files, secrets, or telemetry. Defender's own cloud and sample-submission settings follow Windows policy. The alert tone is a locally synthesized approximation of the Canadian Alert Ready attention signal, not an official broadcast recording. Use the dashboard's alert preview only in a private environment.

## Testing
Use the built-in alert preview for the fullscreen UI and use the official EICAR anti-malware test file in an isolated VM for Defender detection; no live malware is required. Windows Defender may intercept EICAR before you can save it. Review Defender protection history for confirmation. The build workflow checks that the program and installer are present and emits a SHA-256 checksum.

MTR is an early, unsigned build. It is not a certified Windows Security Center antivirus provider. Do not use it as your only security layer.
