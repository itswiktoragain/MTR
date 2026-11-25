"""Windows protection backend. No third-party driver or security-provider registration."""
import base64
import ctypes
from ctypes import wintypes as W
import json
import os
import subprocess
import threading
import xml.etree.ElementTree as ET
from PySide6.QtCore import QObject, Signal

CHANNEL = "Microsoft-Windows-Windows Defender/Operational"
EVENTS = {1116: ("Threat detected", "warning"), 1117: ("Remediation reported", "info"),
          1118: ("Remediation failed", "warning"), 1121: ("Attack surface rule blocked activity", "warning"),
          5001: ("Real-time protection disabled", "warning"), 5007: ("Protection configuration changed", "info")}
NS = {"e": "http://schemas.microsoft.com/win/2004/08/events/event"}
RULES = ("9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2",
         "be9ba2d9-53ea-4cdc-84e5-9b1eeee46550",
         "d4f940ab-401b-4efc-aadc-ad5f3c50688a")
HEALTH_SCRIPT = """$s=Get-MpComputerStatus
[pscustomobject]@{
 antivirus=$s.AntivirusEnabled
 realtime=$s.RealTimeProtectionEnabled
 behavior=$s.BehaviorMonitorEnabled
 ioav=$s.IoavProtectionEnabled
 signature=$s.AntivirusSignatureVersion
 updated=if($s.AntivirusSignatureLastUpdated){$s.AntivirusSignatureLastUpdated.ToString('yyyy-MM-dd HH:mm')}
 quick=if($s.QuickScanEndTime){$s.QuickScanEndTime.ToString('yyyy-MM-dd HH:mm')}
 full=if($s.FullScanEndTime){$s.FullScanEndTime.ToString('yyyy-MM-dd HH:mm')}
}|ConvertTo-Json -Compress"""

def encoded(script):
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")

def powershell(script, elevate=False, timeout=30):
    if os.name != "nt":
        raise RuntimeError("Windows Defender requires Windows.")
    script = "$ErrorActionPreference='Stop'; [Console]::OutputEncoding=[Text.Encoding]::UTF8; " + script
    exe = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "WindowsPowerShell", "v1.0", "powershell.exe")
    if elevate:
        child = encoded(script)
        script = ("$ErrorActionPreference='Stop'; "
                  "$p=Start-Process -FilePath '" + exe.replace("'", "''") +
                  "' -ArgumentList '-NoProfile','-NonInteractive','-EncodedCommand','" + child +
                  "' -Verb RunAs -WindowStyle Hidden -Wait -PassThru; exit $p.ExitCode")
    p = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded(script)],
                       capture_output=True, encoding="utf-8", errors="replace",
                       creationflags=subprocess.CREATE_NO_WINDOW, timeout=timeout)
    if p.returncode:
        raise RuntimeError(p.stderr.strip()[:400] or "Operation failed, was cancelled, or was blocked by Windows policy.")
    return p.stdout.strip()

def parse_event(xml):
    root = ET.fromstring(xml)
    system = root.find("e:System", NS)
    event_id = int(system.findtext("e:EventID", "0", NS))
    if event_id not in EVENTS:
        return None
    fields = {node.get("Name", "Data"): node.text or "" for node in root.findall("e:EventData/e:Data", NS)}
    title, level = EVENTS[event_id]
    relevant = []
    for name in ("Threat Name", "Path", "Process Name", "Action Name", "Error Description", "Rule ID", "Detection User"):
        if fields.get(name):
            relevant.append(name + ": " + fields[name])
    if not relevant:
        relevant = ["Windows Defender event " + str(event_id) + ". See Windows Security or Event Viewer for details."]
    stamp = system.find("e:TimeCreated", NS)
    return {"id": event_id, "title": title, "level": level,
            "detail": "\n".join(relevant), "time": stamp.get("SystemTime", "") if stamp is not None else ""}

def event_stream(stop, emit, status):
    """Pull new events directly from the Windows Event Log API (no periodic PS processes)."""
    if os.name != "nt":
        status(False, "Windows Event Log is unavailable.")
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    evt = ctypes.WinDLL("wevtapi", use_last_error=True)
    H = W.HANDLE
    D = W.DWORD
    B = W.BOOL
    kernel.CreateEventW.argtypes = [ctypes.c_void_p, B, B, W.LPCWSTR]
    kernel.CreateEventW.restype = H
    kernel.WaitForSingleObject.argtypes = [H, D]
    kernel.WaitForSingleObject.restype = D
    kernel.ResetEvent.argtypes = [H]
    kernel.ResetEvent.restype = B
    kernel.CloseHandle.argtypes = [H]
    kernel.CloseHandle.restype = B
    evt.EvtSubscribe.argtypes = [H, H, W.LPCWSTR, W.LPCWSTR, H, ctypes.c_void_p, ctypes.c_void_p, D]
    evt.EvtSubscribe.restype = H
    evt.EvtNext.argtypes = [H, D, ctypes.POINTER(H), D, D, ctypes.POINTER(D)]
    evt.EvtNext.restype = B
    evt.EvtRender.argtypes = [H, H, D, D, ctypes.c_void_p, ctypes.POINTER(D), ctypes.POINTER(D)]
    evt.EvtRender.restype = B
    evt.EvtClose.argtypes = [H]
    evt.EvtClose.restype = B
    signal = kernel.CreateEventW(None, True, False, None)
    if not signal:
        status(False, str(ctypes.WinError(ctypes.get_last_error())))
        return
    subscription = None
    try:
        query = "*[System[" + " or ".join("EventID="+str(i) for i in EVENTS) + "]]"
        subscription = evt.EvtSubscribe(None, signal, CHANNEL, query, None, None, None, 1)
        if not subscription:
            raise ctypes.WinError(ctypes.get_last_error())
        status(True, "Listening to Windows Defender events.")
        handles = (H * 16)()
        while not stop.is_set():
            wait = kernel.WaitForSingleObject(signal, 500)
            if wait == 258:
                continue
            if wait != 0:
                raise ctypes.WinError(ctypes.get_last_error())
            kernel.ResetEvent(signal)
            while not stop.is_set():
                count = D()
                if not evt.EvtNext(subscription, len(handles), handles, 0, 0, ctypes.byref(count)):
                    code = ctypes.get_last_error()
                    if code in (259, 1460):
                        break
                    raise ctypes.WinError(code)
                for i in range(count.value):
                    handle = handles[i]
                    try:
                        needed, properties = D(), D()
                        evt.EvtRender(None, handle, 1, 0, None, ctypes.byref(needed), ctypes.byref(properties))
                        if needed.value:
                            buf = ctypes.create_string_buffer(needed.value)
                            if evt.EvtRender(None, handle, 1, needed.value, buf, ctypes.byref(needed), ctypes.byref(properties)):
                                event = parse_event(ctypes.wstring_at(ctypes.addressof(buf)))
                                if event:
                                    emit(event)
                    except Exception:
                        pass
                    finally:
                        evt.EvtClose(handle)
    except Exception as exc:
        status(False, "Event monitoring unavailable: " + str(exc))
    finally:
        if subscription:
            evt.EvtClose(subscription)
        kernel.CloseHandle(signal)

class Backend(QObject):
    completed = Signal(str, object, str)
    detection = Signal(object)
    monitor_status = Signal(bool, str)
    def __init__(self, parent=None):
        super().__init__(parent)
        self.stop_event = threading.Event()
        self.running = set()
        self.monitor = None

    def watch(self):
        if self.monitor and self.monitor.is_alive():
            return
        self.monitor = threading.Thread(target=event_stream, args=(self.stop_event, self.detection.emit, self.monitor_status.emit), daemon=True)
        self.monitor.start()

    def run(self, key, script, elevate=False, timeout=30):
        if key in self.running:
            return False
        self.running.add(key)
        def worker():
            try:
                result = powershell(script, elevate, timeout)
                if key == "health":
                    result = json.loads(result.lstrip("\ufeff"))
                if not self.stop_event.is_set():
                    self.completed.emit(key, result, "")
            except Exception as exc:
                if not self.stop_event.is_set():
                    self.completed.emit(key, None, str(exc))
        threading.Thread(target=worker, daemon=True).start()
        return True

    def health(self):
        self.run("health", HEALTH_SCRIPT)

    def scan(self, full=False):
        return self.run("scan", "Start-MpScan -ScanType " + ("FullScan" if full else "QuickScan"), True, None)

    def update(self):
        return self.run("update", "Update-MpSignature", True, 900)

    def harden(self, block):
        mode = "Enabled" if block else "AuditMode"
        ids = ",".join("'" + rule + "'" for rule in RULES)
        modes = ",".join("'" + mode + "'" for _ in RULES)
        return self.run("harden", "Add-MpPreference -AttackSurfaceReductionRules_Ids @(" + ids +
                        ") -AttackSurfaceReductionRules_Actions @(" + modes + ")", True, 300)
