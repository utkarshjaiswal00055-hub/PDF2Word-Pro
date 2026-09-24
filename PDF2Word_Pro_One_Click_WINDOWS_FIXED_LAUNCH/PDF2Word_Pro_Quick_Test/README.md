# PDF2Word Pro — one-click Windows launcher

This version does **not** use `START.bat`.

## One-time setup

1. Make sure Python 3.10+ is installed.
2. Extract this ZIP to a normal folder.
3. Open that folder in File Explorer.
4. Right-click `SETUP_ONCE.ps1` → **Run with PowerShell**.
   - If Windows says the script was downloaded from the internet and blocks it:
     right-click the file → **Properties** → check **Unblock** (if shown) → Apply.
5. The setup creates `.venv`, installs the requirements, and creates:
   **PDF2Word Pro.lnk**

## After setup

Just **double-click `PDF2Word Pro.lnk`**.

It will:
- start the PDF2Word server using the private `.venv`
- wait briefly
- open `http://127.0.0.1:5000`

No Command Prompt commands, no virtual-environment activation, and no `START.bat`.

Keep the PowerShell/server window open while using the website. Closing that window stops the server.

## OCR

For scanned PDFs, Tesseract OCR must also be installed and available on PATH. See `OCR_SETUP.txt`.
