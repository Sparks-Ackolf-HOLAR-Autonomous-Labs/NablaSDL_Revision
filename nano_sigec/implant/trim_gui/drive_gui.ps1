# Runs TRIM with its plot window in the logged-in desktop session of sparksone
# and saves an image of each TRIM window. Started by a scheduled task
# (LogonType Interactive), because a TRIM started over SSH has no desktop.
#
# The sparksone console is locked (LogonUI), so a plain screen grab returns the
# lock-screen backdrop. Windows still draw into their DWM surfaces while the
# session is locked, so each TRIM window is rendered with PrintWindow
# (PW_RENDERFULLCONTENT) once TRIM has finished and is idle.
# ShowWindowAsync, not ShowWindow: TRIM does not pump messages while it
# computes, so a synchronous call would block until the run ends.
#
# Usage: drive_gui.ps1 -RecipeList "a;b" -TimeoutS 240
# (one string split here: under -File, "15,40" binds to [int] as 1540)
param([string]$RecipeList, [int]$TimeoutS = 240)
$Recipes = $RecipeList.Split(";")
$work = "C:\Users\admin\trim_gui"
$srim = "C:\SRIM-2013"
$log = "$work\drive.log"
Add-Type -AssemblyName System.Drawing
Add-Type @"
using System; using System.Text; using System.Collections.Generic; using System.Runtime.InteropServices;
public class W {
  public delegate bool EnumProc(IntPtr h, IntPtr l);
  [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
  [DllImport("user32.dll")] public static extern bool ShowWindowAsync(IntPtr h, int c);
  [DllImport("user32.dll")] public static extern bool EnumWindows(EnumProc f, IntPtr l);
  [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr h);
  [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr h, out uint pid);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr hdc, uint flags);
  public struct RECT { public int L, T, R, B; }
  public static List<IntPtr> Windows(uint pid) {
    var res = new List<IntPtr>();
    EnumWindows((h, l) => { uint p; GetWindowThreadProcessId(h, out p);
      if (p == pid && IsWindowVisible(h)) res.Add(h); return true; }, IntPtr.Zero);
    return res;
  }
}
"@
[void][W]::SetProcessDPIAware()
function Grab($h, $path) {
  $r = New-Object W+RECT
  [void][W]::GetWindowRect($h, [ref]$r)
  $w = $r.R - $r.L; $ht = $r.B - $r.T
  if ($w -le 0 -or $ht -le 0) { return "empty rect" }
  $bmp = New-Object System.Drawing.Bitmap $w, $ht
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $dc = $g.GetHdc()
  $ok = [W]::PrintWindow($h, $dc, 2)
  $g.ReleaseHdc($dc)
  $bmp.Save($path, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
  return "ok=$ok ${w}x$ht"
}
"start $(Get-Date -Format o) recipes=$($Recipes -join ',')" | Out-File $log
$autoBackup = (Get-Content "$srim\TRIMAUTO" -Raw).Trim()
try {
  Set-Content "$srim\TRIMAUTO" "0"
  foreach ($r in $Recipes) {
    Copy-Item "$work\inputs\$r.TRIM.IN" "$srim\TRIM.IN" -Force
    $p = Start-Process "$srim\TRIM.exe" -WorkingDirectory $srim -PassThru
    "$r started pid=$($p.Id)" | Out-File $log -Append
    Start-Sleep 5
    foreach ($h in [W]::Windows([uint32]$p.Id)) { [void][W]::ShowWindowAsync($h, 3) }
    # wait until TRIM stops using CPU (calculation finished) or timeout
    $last = -1; $still = 0; $t = 0
    while ($t -lt $TimeoutS -and $still -lt 3) {
      Start-Sleep 3; $t += 3; $p.Refresh()
      $cpu = $p.TotalProcessorTime.TotalSeconds
      if ([math]::Abs($cpu - $last) -lt 0.05) { $still++ } else { $still = 0 }
      $last = $cpu
    }
    "$r idle after ${t}s cpu=$([math]::Round($last,1))s" | Out-File $log -Append
    $i = 0
    foreach ($h in [W]::Windows([uint32]$p.Id)) {
      $res = Grab $h "$work\screens\${r}_win$i.png"
      "$r window $i $res" | Out-File $log -Append
      $i++
    }
    Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
    Start-Sleep 2
  }
} finally {
  Get-Process TRIM -ErrorAction SilentlyContinue | Stop-Process -Force
  Set-Content "$srim\TRIMAUTO" $autoBackup
  "done $(Get-Date -Format o) TRIMAUTO=$((Get-Content "$srim\TRIMAUTO").Trim())" | Out-File $log -Append
}
