"""MTR Antivirus -- native Qt 6 Windows desktop interface."""
import array
import math
import os
from pathlib import Path
import struct
import sys
import tempfile
import wave
from datetime import datetime

from PySide6.QtCore import Qt, QSettings, QTimer, QStandardPaths, QLockFile, QByteArray, QBuffer, QIODevice, QSize, QUrl
from PySide6.QtGui import QIcon, QPixmap, QPainter, QFont, QCursor, QDesktopServices
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QFrame, QLabel, QPushButton,
    QVBoxLayout, QHBoxLayout, QStackedWidget, QScrollArea, QButtonGroup, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView, QLineEdit, QCheckBox, QDialog, QMessageBox, QSystemTrayIcon,
    QMenu, QSizePolicy, QPlainTextEdit)
from mtr_backend import Backend

PATHS = {
    "shield": '<path d="M12 2.4 21 6v6c0 5.3-3.7 8.8-9 10-5.3-1.2-9-4.7-9-10V6z"/><path d="m8 12 2.7 2.7 5.7-6"/>',
    "home": '<path d="m3 10 9-7 9 7v10h-6v-7H9v7H3z"/>',
    "scan": '<path d="M8 3H3v5m13-5h5v5M3 16v5h5m13-5v5h-5M3 12h18"/><path d="M8 8h8v8H8z"/>',
    "history": '<path d="M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5m4-2v6l4 2"/>',
    "settings": '<path d="m10 2-.7 3-2 .9-2.8-1.5-2.1 3.7 2.4 2v2.3l-2.4 2 2.1 3.7 2.8-1.5 2 .9.7 3h4l.7-3 2-.9 2.8 1.5 2.1-3.7-2.4-2v-2.3l2.4-2-2.1-3.7-2.8 1.5-2-.9-.7-3z"/><circle cx="12" cy="11.2" r="3"/>',
    "refresh": '<path d="M20 8a8.5 8.5 0 1 0 .2 8M20 3v5h-5"/>',
    "warning": '<path d="m12 3 10 18H2z"/><path d="M12 9v5m0 3h.01"/>',
    "external": '<path d="M13 4h7v7m0-7-9 9M9 4H4v16h16v-5"/>',
    "check": '<path d="m5 12 5 5L20 7"/>',
    "mute": '<path d="M3 9h4l5-4v14l-5-4H3zM16 9l5 6m0-6-5 6"/>',
}
def icon(name, color="#445364", size=24):
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
           'fill="none" stroke="'+color+'" stroke-width="1.65" stroke-linecap="round" stroke-linejoin="round">'
           + PATHS[name] + '</svg>')
    pix = QPixmap(size, size)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(QByteArray(svg.encode())).render(painter)
    painter.end()
    return QIcon(pix)

def logo_pix(size=48):
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48"><rect width="48" height="48" rx="10" fill="#1755a2"/><path d="M24 8 39 14v10c0 8-6.4 13.3-15 16-8.6-2.7-15-8-15-16V14z" fill="#fff"/><path d="m15.5 27 4-9 4.5 6 4.5-6 4 9" fill="none" stroke="#1755a2" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/></svg>"""
    pix=QPixmap(size,size); pix.fill(Qt.GlobalColor.transparent)
    painter=QPainter(pix); QSvgRenderer(QByteArray(svg.encode())).render(painter); painter.end()
    return pix

def make_ico(path):
    png=QByteArray(); buf=QBuffer(png); buf.open(QIODevice.OpenModeFlag.WriteOnly)
    logo_pix(256).save(buf, "PNG"); buf.close()
    data=bytes(png)
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_bytes(struct.pack("<HHHBBBBHHII",0,1,1,0,0,0,0,1,32,len(data),22)+data)

STYLE = """
QWidget { color:#1c2530; font-family:"Segoe UI"; font-size:10pt; }
QMainWindow { background:#f7f8fa; }
QFrame#rail { background:#edf1f5; border-right:1px solid #dce2e8; }
QLabel#brand { font-size:16pt; font-weight:700; }
QLabel#small, QLabel#muted { color:#647182; }
QLabel#pageTitle { font-size:25pt; font-weight:650; }
QLabel#section { font-size:13pt; font-weight:600; }
QLabel#heroTitle { font-size:21pt; font-weight:650; }
QLabel#value { font-size:12pt; font-weight:600; }
QLabel#stateGood { color:#17633f; font-weight:600; }
QLabel#stateBad { color:#a92d33; font-weight:600; }
QLabel#stateUnknown { color:#6b7784; font-weight:600; }
QFrame#surface { background:#ffffff; border:1px solid #e0e5eb; border-radius:10px; }
QFrame#hero { background:#f1f7f4; border:1px solid #d4e6db; border-radius:12px; }
QFrame#hero[health="bad"] { background:#fff1f1; border-color:#e9c9ca; }
QFrame#hero[health="unknown"] { background:#f0f3f7; border-color:#dce2e8; }
QPushButton { background:#fff; border:1px solid #cdd5de; border-radius:6px; padding:9px 14px; font-weight:500; }
QPushButton:hover { background:#edf4fb; border-color:#a8c2df; }
QPushButton:pressed { background:#dce9f6; }
QPushButton:disabled { color:#9aa4ae; background:#eef1f4; border-color:#e2e6ea; }
QPushButton#primary { background:#1755a2; border-color:#1755a2; color:white; font-weight:600; }
QPushButton#primary:hover { background:#1c65bb; }
QPushButton#primary:disabled { background:#b5c3d4; border-color:#b5c3d4; }
QPushButton#nav { background:transparent; border:0; padding:12px 14px; text-align:left; font-weight:500; }
QPushButton#nav:hover { background:#dfe6ed; }
QPushButton#nav:checked { background:#d7e5f4; color:#154f92; font-weight:600; border-left:3px solid #1755a2; padding-left:11px; }
QPushButton#nav:focus { border:1px solid #729ccb; }
QScrollArea { border:0; background:transparent; }
QScrollArea > QWidget > QWidget { background:transparent; }
QTableWidget { background:#fff; alternate-background-color:#f6f8fa; border:1px solid #dfe4e9; border-radius:7px; selection-background-color:#d7e5f4; selection-color:#152b44; gridline-color:#e3e8ed; }
QHeaderView::section { background:#edf1f5; border:0; border-bottom:1px solid #dce2e8; padding:9px 6px; font-weight:600; color:#3c4c5e; }
QLineEdit, QPlainTextEdit { background:#fff; border:1px solid #ccd5df; border-radius:6px; padding:8px; }
QLineEdit:focus, QPlainTextEdit:focus { border-color:#1755a2; }
QCheckBox { spacing:10px; padding:6px 0; }
QScrollBar:vertical { width:10px; background:transparent; }
QScrollBar::handle:vertical { background:#bdc8d2; border-radius:4px; min-height:28px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height:0; }
"""

def label(text="", name=None, wrap=False):
    obj=QLabel(text)
    obj.setTextFormat(Qt.TextFormat.PlainText)
    if name: obj.setObjectName(name)
    obj.setWordWrap(wrap)
    return obj

def vbox(widget=None, margins=(0,0,0,0), spacing=12):
    layout=QVBoxLayout(widget); layout.setContentsMargins(*margins); layout.setSpacing(spacing); return layout

def hbox(widget=None, margins=(0,0,0,0), spacing=10):
    layout=QHBoxLayout(widget); layout.setContentsMargins(*margins); layout.setSpacing(spacing); return layout

def panel(name="surface"):
    frame=QFrame(); frame.setObjectName(name); return frame

def button(text, callback, symbol=None, primary=False):
    b=QPushButton(text)
    if symbol: b.setIcon(icon(symbol, "#ffffff" if primary else "#445364", 18))
    if primary: b.setObjectName("primary")
    b.clicked.connect(lambda _checked=False: callback())
    b.setCursor(Qt.CursorShape.PointingHandCursor)
    return b

def status_name(value):
    return "stateGood" if value is True else "stateBad" if value is False else "stateUnknown"

def set_state(widget, value):
    widget.setText("Active" if value is True else "Off" if value is False else "Not verified")
    widget.setObjectName(status_name(value)); widget.style().unpolish(widget); widget.style().polish(widget)

def windows_security():
    QDesktopServices.openUrl(QUrl("windowsdefender:"))

class Alert(QDialog):
    def __init__(self, event, audio_path, sound, test=False):
        super().__init__(None, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.played=False; self.audio_path=audio_path; self.sound=sound
        self.setWindowTitle("MTR Security Alert")
        self.setStyleSheet("""QDialog{background:#6e1820} QLabel{color:#fff} QPlainTextEdit{background:#501117;color:#fff;border:1px solid #a35258;border-radius:8px;padding:16px;font-size:13pt} QPushButton{background:#fff;color:#551119;border:0;padding:14px 22px;font-size:12pt} QPushButton:hover{background:#f2dce0} QPushButton#quiet{background:#83323a;color:#fff;border:1px solid #c1797d}""")
        outer=vbox(self,(64,44,64,44),18)
        outer.addStretch(1)
        row=hbox(spacing=14); warning=QLabel(); warning.setPixmap(icon("warning","#ffffff",42).pixmap(42,42)); row.addWidget(warning)
        heading=label("MTR  /  TEST ALERT" if test else "MTR  /  SECURITY ALERT"); heading.setStyleSheet("font-size:15pt;font-weight:650"); row.addWidget(heading); row.addStretch(); outer.addLayout(row)
        title=label(event["title"],wrap=True); title.setStyleSheet("font-size:34pt;font-weight:650"); outer.addWidget(title)
        note=label("This is only a test. No malware was detected." if test else "Windows Defender reported a security event. Review the action and remediation status.",wrap=True); note.setStyleSheet("font-size:14pt;color:#f5d9db"); outer.addWidget(note)
        details=QPlainTextEdit(event.get("detail","")); details.setReadOnly(True); details.setMaximumHeight(240); outer.addWidget(details)
        controls=hbox(); controls.addWidget(button("Open Windows Security", windows_security, "external")); silence=button("Silence alarm",self.silence); silence.setObjectName("quiet"); controls.addWidget(silence); controls.addWidget(button("Dismiss alert",self.accept)); controls.addStretch(); outer.addLayout(controls)
        hint=label("Esc dismisses the alert. MTR never locks your desktop."); hint.setStyleSheet("color:#f5d9db"); outer.addWidget(hint); outer.addStretch(1)
        self.finished.connect(lambda _:self.silence())

    def present(self):
        screen=QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen: self.setGeometry(screen.geometry())
        self.showFullScreen(); self.raise_(); self.activateWindow()
        if self.sound and os.name=="nt":
            try:
                import winsound
                winsound.PlaySound(self.audio_path,winsound.SND_FILENAME | winsound.SND_ASYNC)
                self.played=True
            except Exception: pass

    def silence(self):
        if self.played:
            try:
                import winsound
                winsound.PlaySound(None,0)
            except Exception: pass
            self.played=False

def create_alarm(path):
    rate=22050
    samples=array.array("h")
    for i in range(rate*4):
        t=i/rate; f=853 if int(t*4)%2==0 else 960
        phase=(t*4)%1
        fade=min(1,phase*60,(1-phase)*60)
        samples.append(int(8500*fade*math.sin(2*math.pi*f*t)))
    with wave.open(str(path),"wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate); out.writeframes(samples.tobytes())

class Dashboard(QMainWindow):
    def __init__(self, test=False):
        super().__init__()
        self.test=test; self.closing=False; self.settings=QSettings("MTR","Antivirus")
        self.backend=Backend(self); self.backend.completed.connect(self.operation_done); self.backend.detection.connect(self.on_detection); self.backend.monitor_status.connect(self.on_monitor)
        self.pending=[]; self.alert=None; self.history=[]; self.state={}; self.monitor_ok=None
        self.alarm_dir=tempfile.TemporaryDirectory(prefix="mtr-alert-"); self.alarm_path=str(Path(self.alarm_dir.name)/"alert.wav"); create_alarm(self.alarm_path)
        self.setWindowTitle("MTR Antivirus"); self.setWindowIcon(QIcon(logo_pix())); self.resize(1060,720); self.setMinimumSize(820,590)
        if not test:
            geometry=self.settings.value("geometry")
            if geometry: self.restoreGeometry(geometry)
        root=QWidget(); self.setCentralWidget(root); shell=hbox(root,spacing=0)
        rail=panel("rail"); rail.setFixedWidth(226); rail_layout=vbox(rail,(14,25,14,18),9)
        brand=hbox(spacing=10); mark=QLabel(); mark.setPixmap(logo_pix(40)); brand.addWidget(mark)
        words=vbox(spacing=0); words.addWidget(label("MTR","brand")); words.addWidget(label("Antivirus","small")); brand.addLayout(words); brand.addStretch(); rail_layout.addLayout(brand); rail_layout.addSpacing(25)
        self.navigation=QButtonGroup(self); self.navigation.setExclusive(True); self.stack=QStackedWidget()
        for index,(title,symbol) in enumerate([("Overview","home"),("Virus scans","scan"),("Detection history","history"),("Settings","settings")]):
            nav=QPushButton(title); nav.setObjectName("nav"); nav.setIcon(icon(symbol)); nav.setIconSize(QSize(20,20)); nav.setCheckable(True); nav.setCursor(Qt.CursorShape.PointingHandCursor); self.navigation.addButton(nav,index); rail_layout.addWidget(nav)
        self.navigation.idClicked.connect(self.stack.setCurrentIndex); self.navigation.button(0).setChecked(True)
        rail_layout.addStretch(); rail_layout.addWidget(label("Windows Defender engine","small",True)); rail_layout.addWidget(label("MTR v0.2.0  •  Preview","small"))
        shell.addWidget(rail); shell.addWidget(self.stack,1)
        self.overview_page(); self.scan_page(); self.history_page(); self.settings_page()
        self.tray=None
        if not test and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray=QSystemTrayIcon(QIcon(logo_pix()),self); self.tray.setToolTip("MTR Antivirus")
            menu=QMenu(self); menu.addAction("Open MTR",self.show_dashboard); menu.addAction("Quick scan",lambda:self.start_scan(False)); menu.addSeparator(); menu.addAction("Exit MTR dashboard",self.quit)
            self.tray.setContextMenu(menu); self.tray.activated.connect(lambda reason:self.show_dashboard() if reason in (QSystemTrayIcon.ActivationReason.DoubleClick,QSystemTrayIcon.ActivationReason.Trigger) else None); self.tray.show()
        self.timer=QTimer(self); self.timer.setInterval(30000); self.timer.timeout.connect(self.backend.health)
        if not test:
            self.backend.watch(); self.backend.health(); self.timer.start()

    def page(self,title,subtitle):
        area=QScrollArea(); area.setWidgetResizable(True); area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        widget=QWidget(); layout=vbox(widget,(30,28,30,28),16)
        layout.addWidget(label(title,"pageTitle")); layout.addWidget(label(subtitle,"muted",True)); layout.addSpacing(6)
        area.setWidget(widget); self.stack.addWidget(area); return layout

    def overview_page(self):
        layout=self.page("Protection overview","Review the current Windows protection status and recent security activity.")
        self.hero=panel("hero"); self.hero.setProperty("health","unknown"); hero=hbox(self.hero,(22,22,22,22),18)
        self.hero_icon=QLabel(); self.hero_icon.setPixmap(icon("shield","#647182",76).pixmap(76,76)); hero.addWidget(self.hero_icon,0,Qt.AlignmentFlag.AlignVCenter)
        info=vbox(spacing=7); self.hero_title=label("Checking protection…","heroTitle",True); self.hero_text=label("Waiting for Windows Defender to report its status.","muted",True); info.addWidget(self.hero_title); info.addWidget(self.hero_text)
        actions=hbox(); actions.addWidget(button("Quick scan",lambda:self.start_scan(False), "scan",True)); actions.addWidget(button("Windows Security",windows_security,"external")); actions.addStretch(); info.addLayout(actions); hero.addLayout(info,1)
        layout.addWidget(self.hero)
        layout.addWidget(label("Protection components","section"))
        surface=panel(); rows=vbox(surface,(17,10,17,10),1); self.states={}
        for key,title,desc in [("realtime","Real-time protection","On-access scanning and blocking"),("behavior","Behavior monitoring","Suspicious activity detection"),("ioav","Downloaded file scanning","Scan internet downloads and attachments"),("antivirus","Antivirus engine","Microsoft Defender Antivirus")]:
            row=hbox(spacing=10); text=vbox(spacing=2); text.addWidget(label(title,"value")); text.addWidget(label(desc,"small",True)); row.addLayout(text,1); state=label("Not verified","stateUnknown"); self.states[key]=state; row.addWidget(state); rows.addLayout(row)
            if key!="antivirus":
                divider=QFrame(); divider.setFrameShape(QFrame.Shape.HLine); divider.setStyleSheet("color:#e8ecf0"); rows.addWidget(divider)
        layout.addWidget(surface)
        status=panel(); box=vbox(status,(18,14,18,14),6); line=hbox(); line.addWidget(label("Detection monitor","section")); line.addStretch(); self.monitor_label=label("Connecting…","stateUnknown"); line.addWidget(self.monitor_label); box.addLayout(line)
        self.monitor_detail=label("Waiting for the Windows Event Log subscription.","muted",True); box.addWidget(self.monitor_detail); self.signature=label("Signatures: not verified","muted",True); box.addWidget(self.signature); layout.addWidget(status); layout.addStretch()

    def scan_page(self):
        layout=self.page("Virus scans","Start an on-demand scan through the installed Microsoft Defender engine.")
        self.scan_buttons=[]; self.scan_dates={}
        for full,title,desc in [(False,"Quick scan","Checks locations commonly used by malware and running threats."),(True,"Full scan","Checks all accessible files and locations. May take several hours.")]:
            frame=panel(); box=vbox(frame,(20,18,20,18),10); box.addWidget(label(title,"section")); box.addWidget(label(desc,"muted",True)); date=label("Last completed: not verified","small"); self.scan_dates[full]=date; box.addWidget(date); row=hbox(); b=button("Start "+title.lower(),lambda full=full:self.start_scan(full),"scan",True); self.scan_buttons.append(b); row.addWidget(b); row.addStretch(); box.addLayout(row); layout.addWidget(frame)
        self.scan_status=label("Ready to scan.","muted",True); layout.addWidget(self.scan_status); layout.addStretch()

    def history_page(self):
        layout=self.page("Detection history","Live security events reported since the MTR dashboard started.")
        row=hbox(); self.filter=QLineEdit(); self.filter.setPlaceholderText("Search events, paths or threat names"); self.filter.textChanged.connect(self.refresh_history); row.addWidget(self.filter,1); row.addWidget(button("Windows Security",windows_security,"external")); layout.addLayout(row)
        self.table=QTableWidget(0,4); self.table.setHorizontalHeaderLabels(["Time","Activity","Status","Event ID"]); self.table.setMinimumHeight(245); self.table.setAlternatingRowColors(True); self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers); self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows); self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection); self.table.verticalHeader().hide()
        for i in (0,2,3): self.table.horizontalHeader().setSectionResizeMode(i,QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1,QHeaderView.ResizeMode.Stretch); self.table.itemSelectionChanged.connect(self.selected_event); layout.addWidget(self.table,1)
        self.details=QPlainTextEdit(); self.details.setReadOnly(True); self.details.setPlaceholderText("Select an event to view its details."); self.details.setMaximumHeight(135); layout.addWidget(self.details)
        self.history_count=label("No events in this session.","small"); layout.addWidget(self.history_count)

    def settings_page(self):
        layout=self.page("Settings","Manage MTR notifications and optional Windows security hardening.")
        notifications=panel(); box=vbox(notifications,(20,18,20,18),10); box.addWidget(label("Threat alerts","section")); box.addWidget(label("Fullscreen alerts appear for detections, failed remediation and selected protection warnings.","muted",True))
        self.sound=QCheckBox("Play the Alert Ready-style attention sound"); self.sound.setChecked(self.settings.value("sound",True,type=bool)); self.sound.toggled.connect(lambda value:self.settings.setValue("sound",value)); box.addWidget(self.sound)
        row=hbox(); row.addWidget(button("Preview fullscreen alert",self.preview,"warning")); row.addStretch(); box.addLayout(row); layout.addWidget(notifications)
        frame=panel(); box=vbox(frame,(20,18,20,18),10); box.addWidget(label("Attack surface reduction","section")); box.addWidget(label("Optional rules for LSASS credential theft, executable email content and Office child processes. These policies may disrupt legitimate software. Audit first.","muted",True)); row=hbox(); self.audit_button=button("Enable audit mode",lambda:self.harden(False)); self.block_button=button("Enable block mode",lambda:self.harden(True)); row.addWidget(self.audit_button); row.addWidget(self.block_button); row.addStretch(); box.addLayout(row); self.harden_status=label("No changes requested in this session.","small",True); box.addWidget(self.harden_status); layout.addWidget(frame)
        frame=panel(); box=vbox(frame,(20,18,20,18),10); box.addWidget(label("Security intelligence","section")); box.addWidget(label("Microsoft Defender manages the signature database. MTR can request an update.","muted",True)); row=hbox(); self.update_button=button("Update signatures",self.update_signatures,"refresh"); row.addWidget(self.update_button); row.addStretch(); box.addLayout(row); self.update_status=label("Ready.","small",True); box.addWidget(self.update_status); layout.addWidget(frame)
        layout.addWidget(label("MTR is a Defender companion, not a certified standalone antivirus. No product can guarantee perfect protection against every threat.","small",True)); layout.addStretch()

    def on_monitor(self,ok,message):
        self.monitor_ok=ok; self.monitor_label.setText("Listening" if ok else "Unavailable"); self.monitor_label.setObjectName("stateGood" if ok else "stateBad"); self.monitor_label.style().unpolish(self.monitor_label); self.monitor_label.style().polish(self.monitor_label); self.monitor_detail.setText(message)

    def render_health(self,data):
        self.state=data or {}
        values=[self.state.get(k) for k in self.states]
        for key,w in self.states.items(): set_state(w,self.state.get(key))
        if all(v is True for v in values):
            key,title,desc,color="good","Protection is active","Windows Defender reports all monitored protection components are enabled.","#17633f"
        elif any(v is False for v in values):
            key,title,desc,color="bad","Protection needs attention","One or more protection components are disabled. Open Windows Security to review.","#a92d33"
        else:
            key,title,desc,color="unknown","Protection not verified","MTR could not verify all protection components. Open Windows Security to check.","#647182"
        self.hero.setProperty("health",key); self.hero.style().unpolish(self.hero); self.hero.style().polish(self.hero)
        self.hero_icon.setPixmap(icon("shield" if key!="bad" else "warning",color,76).pixmap(76,76)); self.hero_title.setText(title); self.hero_text.setText(desc)
        self.signature.setText("Signatures: "+str(self.state.get("signature") or "not verified")+"  •  Updated: "+str(self.state.get("updated") or "unknown"))
        for full,date in self.scan_dates.items(): date.setText("Last completed: "+str(self.state.get("full" if full else "quick") or "not verified"))

    def operation_done(self,key,result,error):
        self.backend.running.discard(key)
        if key=="health": self.render_health(result if not error else {}); return
        status=("Operation failed: "+error) if error else "Operation completed."
        if key=="scan":
            for b in self.scan_buttons:b.setEnabled(True)
            self.scan_status.setText(status+" Check Windows Security for scan results.")
        elif key=="update":self.update_button.setEnabled(True); self.update_status.setText(status)
        elif key=="harden":
            self.audit_button.setEnabled(True); self.block_button.setEnabled(True); self.harden_status.setText(status)
        self.add_history({"time":datetime.now().isoformat(),"title":{"scan":"Scan","update":"Signature update","harden":"Policy change"}.get(key,key),"level":"warning" if error else "info","detail":status,"id":"—"})
        self.backend.health()

    def start_scan(self,full):
        if self.test:return
        if self.backend.scan(full):
            for b in self.scan_buttons:b.setEnabled(False)
            self.scan_status.setText("Scan requested. Approve the Windows elevation prompt if shown.")
            self.navigation.button(1).setChecked(True); self.stack.setCurrentIndex(1)

    def update_signatures(self):
        if self.backend.update():self.update_button.setEnabled(False); self.update_status.setText("Update requested. Approve the Windows elevation prompt if shown.")

    def harden(self,block):
        choice=QMessageBox.question(self,"Change Defender policy","Configure three attack surface reduction rules in "+("block" if block else "audit")+" mode? Existing values for these rules may change. Review and revert via Windows security policy if necessary.")
        if choice==QMessageBox.StandardButton.Yes and self.backend.harden(block):
            self.audit_button.setEnabled(False); self.block_button.setEnabled(False); self.harden_status.setText("Policy change requested. Approve the Windows elevation prompt if shown.")

    def add_history(self,event):
        self.history.insert(0,event); del self.history[500:]; self.refresh_history()

    def refresh_history(self,*_):
        search=self.filter.text().casefold()
        matching=[e for e in self.history if search in (e["title"]+" "+e["detail"]+" "+str(e["id"])).casefold()]
        self.table.setRowCount(len(matching))
        for row,e in enumerate(matching):
            stamp=e["time"]
            try:stamp=datetime.fromisoformat(stamp.replace("Z","+00:00")).astimezone().strftime("%H:%M:%S")
            except ValueError:pass
            for col,value in enumerate([stamp,e["title"],"Attention" if e["level"]=="warning" else "Information",str(e["id"])]):
                item=QTableWidgetItem(value); item.setData(Qt.ItemDataRole.UserRole,e); self.table.setItem(row,col,item)
        self.history_count.setText(str(len(matching))+" shown  •  "+str(len(self.history))+" in this session")

    def selected_event(self):
        items=self.table.selectedItems()
        self.details.setPlainText((items[0].data(Qt.ItemDataRole.UserRole) or {}).get("detail","") if items else "")

    def on_detection(self,event):
        self.add_history(event)
        if event["level"]=="warning":
            self.pending.append((event,False)); self.next_alert()
        if event["id"] in (5001,5007):self.backend.health()

    def preview(self):
        self.pending.append(({"title":"Security alert preview","detail":"Example detection notification.\n\nNo malware was detected. The alarm is a locally synthesized approximation of the Canadian Alert Ready attention signal."},True)); self.next_alert()

    def next_alert(self):
        if self.alert or not self.pending or self.closing:return
        event,test=self.pending.pop(0); self.alert=Alert(event,self.alarm_path,self.sound.isChecked() and not self.test,test)
        self.alert.finished.connect(self.alert_closed); self.alert.present()

    def alert_closed(self,*_):
        if self.alert:self.alert.deleteLater()
        self.alert=None; QTimer.singleShot(0,self.next_alert)

    def show_dashboard(self):
        self.showNormal(); self.raise_(); self.activateWindow()

    def closeEvent(self,event):
        if self.tray and not self.closing:
            event.ignore(); self.hide()
        else:
            self.settings.setValue("geometry",self.saveGeometry()); event.accept()
            if not self.closing: QTimer.singleShot(0,self.quit)

    def quit(self):
        self.closing=True; self.settings.setValue("geometry",self.saveGeometry()); self.backend.stop_event.set(); self.timer.stop()
        if self.alert:self.alert.reject()
        if self.tray:self.tray.hide()
        self.alarm_dir.cleanup(); QApplication.instance().quit()

def main():
    app=QApplication(sys.argv); app.setApplicationName("MTR Antivirus"); app.setOrganizationName("MTR"); app.setStyle("Fusion"); app.setFont(QFont("Segoe UI",10)); app.setStyleSheet(STYLE); app.setWindowIcon(QIcon(logo_pix()))
    if "--make-icon" in sys.argv:
        make_ico(sys.argv[sys.argv.index("--make-icon")+1]); return 0
    if "--smoke-test" in sys.argv:
        window=Dashboard(True); window.render_health({"antivirus":True,"realtime":True,"behavior":True,"ioav":True,"signature":"test","updated":"preview"}); window.on_monitor(True,"Example status for UI smoke test."); window.show(); app.processEvents()
        if "--screenshot" in sys.argv:
            window.grab().save(sys.argv[sys.argv.index("--screenshot")+1])
        for i in range(4): window.stack.setCurrentIndex(i); app.processEvents()
        window.preview(); app.processEvents()
        assert window.alert is not None and window.stack.count()==4
        window.alert.reject(); app.processEvents(); window.quit(); return 0
    app.setQuitOnLastWindowClosed(False)
    data=Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)); data.mkdir(parents=True,exist_ok=True)
    lock=QLockFile(str(data/"dashboard.lock"))
    server_name="MTRDashboard-"+__import__("hashlib").sha256(str(data).encode()).hexdigest()[:20]
    if not lock.tryLock(0):
        socket=QLocalSocket(); socket.connectToServer(server_name); socket.waitForConnected(1000); return 0
    server=QLocalServer(); QLocalServer.removeServer(server_name); server.listen(server_name)
    window=Dashboard()
    def wake():
        while server.hasPendingConnections():
            peer=server.nextPendingConnection(); peer.disconnectFromServer(); peer.deleteLater()
        window.show_dashboard()
    server.newConnection.connect(wake)
    app.aboutToQuit.connect(window.backend.stop_event.set)
    if "--background" not in sys.argv or window.tray is None:window.show()
    return app.exec()

if __name__=="__main__":
    sys.exit(main())
