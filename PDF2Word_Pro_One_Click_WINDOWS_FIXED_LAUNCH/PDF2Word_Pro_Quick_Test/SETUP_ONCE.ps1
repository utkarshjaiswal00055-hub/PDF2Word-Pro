$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "PDF2Word Pro - one-time setup" -ForegroundColor Cyan
Write-Host ""

# Find Python launcher or python.exe
$Py = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    $Py = (Get-Command py).Source
    $PyArgs = @("-3")
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $Py = (Get-Command python).Source
    $PyArgs = @()
} else {
    Write-Host "Python was not found. Install Python 3.10+ first." -ForegroundColor Red
    Read-Host "Press Enter to close"
    exit 1
}

if (-not (Test-Path "$Root\.venv\Scripts\python.exe")) {
    Write-Host "Creating the private environment..."
    & $Py @PyArgs -m venv "$Root\.venv"
    if ($LASTEXITCODE -ne 0) { throw "Could not create the virtual environment." }
}

$Vpy = "$Root\.venv\Scripts\python.exe"
Write-Host "Installing required packages..."
& $Vpy -m pip install --upgrade pip
& $Vpy -m pip install -r "$Root\requirements.txt"
if ($LASTEXITCODE -ne 0) { throw "Package installation failed." }

$tess = Get-Command tesseract -ErrorAction SilentlyContinue
if (-not $tess) {
    Write-Host "Note: Tesseract OCR was not found. Digital PDFs will work; scanned PDFs need Tesseract installed." -ForegroundColor Yellow
}

# Create a Windows shortcut that calls the robust PowerShell launcher.
# The launcher uses the shortcut's working folder, so it never depends on
# $MyInvocation inside an inline -Command block.
$ShortcutPath = Join-Path $Root "PDF2Word Pro.lnk"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath = "$env:SystemRoot\System32\WindowsPowerShell\v1.0\powershell.exe"
$Shortcut.Arguments = "-NoProfile -ExecutionPolicy Bypass -File `"$Root\LAUNCH.ps1`""
$Shortcut.WorkingDirectory = $Root
$Shortcut.Description = "Start PDF2Word Pro"
$Shortcut.IconLocation = "$env:SystemRoot\System32\SHELL32.dll,220"
$Shortcut.Save()

Write-Host ""
Write-Host "Setup complete." -ForegroundColor Green
Write-Host "From now on, double-click 'PDF2Word Pro.lnk' to start the app." -ForegroundColor Green
Write-Host "You do NOT need to activate the virtual environment manually."
Write-Host ""
Read-Host "Press Enter to close"
