$ErrorActionPreference = "Stop"
Add-Type -AssemblyName System.Windows.Forms
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$Vpy = Join-Path $Root ".venv\Scripts\python.exe"
$HealthUrl = "http://127.0.0.1:5000/health"
$AppUrl = "http://127.0.0.1:5000/"

if (-not (Test-Path $Vpy)) {
    [System.Windows.Forms.MessageBox]::Show("PDF2Word Pro is not set up yet. Run SETUP_ONCE.ps1 first.", "PDF2Word Pro")
    exit 1
}

# If another copy is already serving the app, reuse it instead of creating a
# second process that will fail because port 5000 is already occupied.
try {
    $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 1
    if ($r.StatusCode -eq 200) {
        Start-Process $AppUrl
        exit 0
    }
} catch {}

$p = Start-Process -FilePath $Vpy -ArgumentList "app.py" -WorkingDirectory $Root -PassThru -WindowStyle Normal

for ($i=0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if ($p.HasExited) {
        [System.Windows.Forms.MessageBox]::Show("PDF2Word Pro stopped unexpectedly. Open PowerShell in the project folder and run: .venv\Scripts\python.exe app.py", "PDF2Word Pro")
        exit 1
    }
    try {
        $r = Invoke-WebRequest -Uri $HealthUrl -UseBasicParsing -TimeoutSec 1
        if ($r.StatusCode -eq 200) {
            Start-Process $AppUrl
            exit 0
        }
    } catch {}
}

[System.Windows.Forms.MessageBox]::Show("PDF2Word Pro did not start within 20 seconds. The server window may contain the error.", "PDF2Word Pro")
exit 1
