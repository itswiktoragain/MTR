# MTR Antivirus — independent engine

MTR v0.3 is a Windows 10/11 x64 antivirus preview built with Qt 6 and the independent open-source ClamAV scanning engine. The old WinForms code is historical only; the installer builds the Python/Qt application. No Defender APIs are used by the active backend.

- Persistent ClamAV daemon bound to loopback, with streaming local scans.
- FreshClam downloads official signed signature databases at first launch and checks periodically; no signatures are bundled initially. Protection is unavailable until download and engine load succeed. Internet access is required for updates.
- Windows filesystem notifications for existing Downloads, Desktop, Documents, Temp and Startup folders; one-second polling of current-user executable images.
- Quick scans of those locations; full scans of readable files under the current user profile.
- 64 MiB file limit, archive/engine limits, inaccessible and reparse-point files skipped; queues are bounded and overflow is reported.
- Fullscreen alerts and a synthesized Alert Ready-style sound. Optional same-volume quarantine for confirmed detections in watched user folders, off by default. Metadata records original paths and hashes; files are moved, not deleted. Restore manually only after confirming a false positive. Quarantine is a user-owned directory, not a hardened sandbox.
- No automatic process termination, kernel driver, process-create interception, memory scanning, or Windows Security Center registration. This is not guaranteed pre-execution blocking, and a running threat may already have acted. Local processes can access the loopback daemon. Keep existing security layers enabled.

## Build
Run `./build.ps1` with Python 3.12 x64 and Inno Setup 6. CI fetches the current official ClamAV x64 ZIP and matching source archive from the Cisco-Talos/clamav GitHub releases, checks SHA-256 against release metadata when available, records the upstream version and hashes, bundles the engine and license files, and tests both source and packaged scanners against an isolated benign marker signature. It also tests the Qt interface and generates a synthetic UI screenshot. The installer is unsigned. The corresponding upstream source is supplied as a separate release asset. ClamAV remains subject to its upstream license.

## Testing
The harmless marker test is performed with its own temporary database and never touches the live database. It checks detection and a clean verdict, not malware efficacy. You can also preview alerts in Settings. Use a disposable VM and standard safe antivirus test files for integration testing, not live malware.
