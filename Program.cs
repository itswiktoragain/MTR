using System.Diagnostics;
using System.Diagnostics.Eventing.Reader;
using System.Media;
using System.Drawing;
using System.Windows.Forms;
using System.IO;

static class Program {
 [STAThread] static void Main() {
  ApplicationConfiguration.Initialize();
  using var mutex = new System.Threading.Mutex(true, @"Local\MTRDashboard", out bool first);
  if(first) Application.Run(new Dashboard());
 }
}
sealed class Dashboard : Form {
 readonly Label health = new(){AutoSize=true, Text="Checking Windows protection...", Font=new Font("Segoe UI",13)};
 readonly ListBox history = new(){Dock=DockStyle.Fill};
 readonly System.Windows.Forms.Timer timer = new(){Interval=30000};
 EventLogWatcher? watcher;
 bool busy, alertOpen;
 readonly NotifyIcon tray = new(){Icon=SystemIcons.Shield, Text="MTR Antivirus", Visible=true};
 public Dashboard(){
  Text="MTR Antivirus"; Size=new Size(810,560); MinimumSize=new Size(620,420); BackColor=Color.White; Font=new Font("Segoe UI",10);
  var layout=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(26),ColumnCount=1,RowCount=5};
  layout.RowStyles.Add(new RowStyle(SizeType.Absolute,65)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute,80)); layout.RowStyles.Add(new RowStyle(SizeType.Absolute,95));layout.RowStyles.Add(new RowStyle(SizeType.Absolute,32));layout.RowStyles.Add(new RowStyle(SizeType.Percent,100));
  layout.Controls.Add(new Label{Text="MTR   /   Antivirus",Font=new Font("Segoe UI",24,FontStyle.Bold),AutoSize=true});
  layout.Controls.Add(health);
  var buttons=new FlowLayoutPanel{Dock=DockStyle.Fill,AutoScroll=true};
  Add(buttons,"Quick scan",async()=>await Scan("QuickScan")); Add(buttons,"Full scan",async()=>await Scan("FullScan"));
  Add(buttons,"Update signatures",async()=>await Action("Update-MpSignature")); Add(buttons,"Security settings",()=>{Process.Start(new ProcessStartInfo("windowsdefender:"){UseShellExecute=true});return Task.CompletedTask;});
  Add(buttons,"Alert preview",()=>{Alert("MTR alert preview","No malware was detected. This is a test.",true);return Task.CompletedTask;});
  Add(buttons,"Hardening (audit)",async()=>await Harden(false)); Add(buttons,"Hardening (block)",async()=>await Harden(true));
  layout.Controls.Add(buttons);layout.Controls.Add(new Label{Text="Live detection history (this session)",AutoSize=true});layout.Controls.Add(history);Controls.Add(layout);
  tray.DoubleClick+=(_,_)=>{Show();WindowState=FormWindowState.Normal;Activate();};
  var menu=new ContextMenuStrip();menu.Items.Add("Open MTR",null,(_,_)=>{Show();Activate();});menu.Items.Add("Exit dashboard",null,(_,_)=>{tray.Visible=false;Application.Exit();});tray.ContextMenuStrip=menu;
  Resize+=(_,_)=>{if(WindowState==FormWindowState.Minimized)Hide();};
  Shown+=async(_,_)=>{Watch();await RefreshHealth();};timer.Tick+=async(_,_)=>await RefreshHealth();timer.Start();
  FormClosed+=(_,_)=>{timer.Dispose();watcher?.Dispose();tray.Dispose();};
 }
 void Add(FlowLayoutPanel p,string text,Func<Task> action){var b=new Button{Text=text,AutoSize=true,Height=34,FlatStyle=FlatStyle.System};b.Click+=async(_,_)=>{try{await action();}catch(Exception ex){Log(ex.Message);}};p.Controls.Add(b);}
 void Log(string s){history.Items.Insert(0,DateTime.Now.ToString("HH:mm:ss")+"  "+s);while(history.Items.Count>500)history.Items.RemoveAt(history.Items.Count-1);}
 void Watch(){
  try{
   watcher=new EventLogWatcher(new EventLogQuery("Microsoft-Windows-Windows Defender/Operational",PathType.LogName,"*[System[(EventID=1116 or EventID=1117 or EventID=1118 or EventID=1121 or EventID=5001 or EventID=5007)]]"));
   watcher.EventRecordWritten+=(_,e)=>{
    if(e.EventException!=null){if(!IsDisposed)BeginInvoke((Action)(()=>Log("Event subscription error: "+e.EventException.Message)));return;}
    using var record=e.EventRecord;if(record==null)return;int id=record.Id;string msg;
    try{msg=record.FormatDescription()??"Defender event "+id;}catch{msg="Defender event "+id;}
    if(!IsDisposed)BeginInvoke((Action)(()=>{Log("Event "+id+": "+msg.Replace("\r"," ").Replace("\n"," "));if(id==1116||id==1118||id==1121||id==5001)Alert(id==5001?"Real-time protection disabled":id==1118?"Remediation failed":id==1121?"Attack surface rule blocked activity":"Threat detected",msg,false);}));
   };watcher.Enabled=true;Log("Defender event monitoring active.");
  }catch(Exception e){Log("Monitoring unavailable: "+e.Message);}
 }
 async Task<string> Power(string script,bool elevated=false){
  var psi=new ProcessStartInfo("powershell.exe"){UseShellExecute=elevated,CreateNoWindow=!elevated,RedirectStandardOutput=!elevated,RedirectStandardError=!elevated,WindowStyle=ProcessWindowStyle.Hidden};
  psi.Arguments="-NoProfile -NonInteractive -EncodedCommand "+Convert.ToBase64String(System.Text.Encoding.Unicode.GetBytes("$ErrorActionPreference='Stop'; "+script));
  if(elevated)psi.Verb="runas";
  using var p=Process.Start(psi)??throw new Exception("PowerShell failed to start");
  if(elevated){await p.WaitForExitAsync();if(p.ExitCode!=0)throw new Exception("Windows rejected the requested operation.");return "";}
  var output=p.StandardOutput.ReadToEndAsync();var error=p.StandardError.ReadToEndAsync();await p.WaitForExitAsync();if(p.ExitCode!=0)throw new Exception(await error);return await output;
 }
 async Task RefreshHealth(){if(busy)return;busy=true;try{
  var s=(await Power("$s=Get-MpComputerStatus; Write-Output ($s.AntivirusEnabled.ToString()+'|'+$s.RealTimeProtectionEnabled.ToString()+'|'+$s.AntivirusSignatureLastUpdated.ToString())")).Trim().Split('|');
  bool ok=s.Length==3&&s[0]=="True"&&s[1]=="True";
  health.Text=ok?"Defender real-time protection is active\nSignatures: "+s[2]:"Protection disabled or unavailable — check Windows Security.";
  health.ForeColor=ok?Color.DarkGreen:Color.DarkRed;
 }catch{health.Text="Unable to verify protection — check Windows Security.";health.ForeColor=Color.DarkRed;}finally{busy=false;}}
 async Task Scan(string kind){Log("Requesting "+kind);await Power("Start-MpScan -ScanType "+kind,true);Log("Scan command completed; see Windows Security for results.");}
 async Task Action(string command){await Power(command,true);Log("Operation completed.");await RefreshHealth();}
 async Task Harden(bool block){
  string mode=block?"Enabled":"AuditMode";
  if(MessageBox.Show("Configure three Microsoft attack surface reduction rules for credential theft from LSASS, executable content from email/webmail, and Office child processes. Existing values for these three rules may change. Block mode may break legitimate software. Manage or revert these settings via Windows security policy. Continue?","MTR hardening",MessageBoxButtons.YesNo,MessageBoxIcon.Warning)!=DialogResult.Yes)return;
  await Action("Add-MpPreference -AttackSurfaceReductionRules_Ids @('9e6c4e1f-7d60-472f-ba1a-a39ef669e4b2','be9ba2d9-53ea-4cdc-84e5-9b1eeee46550','d4f940ab-401b-4efc-aadc-ad5f3c50688a') -AttackSurfaceReductionRules_Actions @('"+mode+"','"+mode+"','"+mode+"')");
 }
 void Alert(string title,string detail,bool test){
  if(alertOpen)return;alertOpen=true;try{using var popup=new ThreatAlert(title,detail,test);popup.ShowDialog();}finally{alertOpen=false;}
 }
}
sealed class ThreatAlert:Form {
 readonly MemoryStream audio=new();readonly SoundPlayer player;
 public ThreatAlert(string title,string detail,bool test){
  FormBorderStyle=FormBorderStyle.None;StartPosition=FormStartPosition.Manual;Bounds=Screen.FromPoint(Cursor.Position).Bounds;TopMost=true;BackColor=Color.FromArgb(125,15,20);ForeColor=Color.White;KeyPreview=true;
  var panel=new TableLayoutPanel{Dock=DockStyle.Fill,Padding=new Padding(70),ColumnCount=1,RowCount=5};panel.RowStyles.Add(new RowStyle(SizeType.Absolute,70));panel.RowStyles.Add(new RowStyle(SizeType.Absolute,110));panel.RowStyles.Add(new RowStyle(SizeType.Percent,100));panel.RowStyles.Add(new RowStyle(SizeType.Absolute,60));panel.RowStyles.Add(new RowStyle(SizeType.Absolute,60));
  panel.Controls.Add(new Label{Text=test?"MTR / TEST ALERT":"MTR / SECURITY ALERT",Font=new Font("Segoe UI",22,FontStyle.Bold),AutoSize=true});
  panel.Controls.Add(new Label{Text=title,Font=new Font("Segoe UI",38,FontStyle.Bold),Dock=DockStyle.Fill});
  panel.Controls.Add(new TextBox{Text=detail,Multiline=true,ReadOnly=true,ScrollBars=ScrollBars.Vertical,Dock=DockStyle.Fill,BackColor=BackColor,ForeColor=Color.White,BorderStyle=BorderStyle.None,Font=new Font("Segoe UI",16)});
  panel.Controls.Add(new Label{Text=test?"This is a simulation.":"Check Windows Security for remediation status. Detection does not necessarily mean removal.",AutoSize=true,Font=new Font("Segoe UI",14)});
  var buttons=new FlowLayoutPanel{Dock=DockStyle.Fill};var open=new Button{Text="Open Windows Security",AutoSize=true,ForeColor=Color.Black};open.Click+=(_,_)=>{Process.Start(new ProcessStartInfo("windowsdefender:"){UseShellExecute=true});Close();};var close=new Button{Text="Dismiss / silence",AutoSize=true,ForeColor=Color.Black};close.Click+=(_,_)=>Close();buttons.Controls.Add(open);buttons.Controls.Add(close);panel.Controls.Add(buttons);Controls.Add(panel);
  KeyDown+=(_,e)=>{if(e.KeyCode==Keys.Escape)Close();};
  // Locally synthesized alternating dual-tone alarm; not an official recording.
  using(var w=new BinaryWriter(audio,System.Text.Encoding.ASCII,true)){int rate=22050,n=rate*4;w.Write("RIFF"u8);w.Write(36+n*2);w.Write("WAVEfmt "u8);w.Write(16);w.Write((short)1);w.Write((short)1);w.Write(rate);w.Write(rate*2);w.Write((short)2);w.Write((short)16);w.Write("data"u8);w.Write(n*2);for(int i=0;i<n;i++){double t=(double)i/rate;double f=(i/(rate/4))%2==0?853:960;double fade=Math.Min(1,Math.Min(i,n-1-i)/220.0);w.Write((short)(8000*fade*Math.Sin(2*Math.PI*f*t)));}}audio.Position=0;player=new SoundPlayer(audio);Shown+=(_,_)=>{try{player.Play();}catch{}};FormClosed+=(_,_)=>{player.Stop();player.Dispose();audio.Dispose();};
 }
}
