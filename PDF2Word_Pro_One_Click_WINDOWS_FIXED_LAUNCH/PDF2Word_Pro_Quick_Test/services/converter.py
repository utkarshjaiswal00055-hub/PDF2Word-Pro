
import fitz
import shutil
from pathlib import Path
from docx import Document
from pdf2docx import Converter

def inspect_pdf(path):
    doc=fitz.open(path); pages=len(doc); text_pages=0; image_pages=0
    for p in doc:
        if p.get_text("text").strip(): text_pages+=1
        if p.get_images(full=True): image_pages+=1
    doc.close()
    kind="digital" if text_pages==pages else ("scanned_or_image" if text_pages==0 else "mixed")
    return {"pages":pages,"text_pages":text_pages,"image_pages":image_pages,"type":kind}

def convert_pdf_to_docx(src,dst):
    cv=Converter(str(src))
    try: cv.convert(str(dst),start=0,end=None)
    finally: cv.close()

def ocr_pdf_to_docx(src,dst):
    try:
        import pytesseract, io
        from PIL import Image
    except ImportError:
        raise RuntimeError("OCR Python dependencies are missing. Run SETUP_ONCE.ps1 again.")

    # Find Tesseract even when it was installed but not added to PATH.
    if not shutil.which("tesseract"):
        candidates = [
            Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
            Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
            Path(r"D:\Tesseract-OCR\tesseract.exe"),
            Path(r"D:\Program Files\Tesseract-OCR\tesseract.exe"),
        ]
        for candidate in candidates:
            if candidate.exists():
                pytesseract.pytesseract.tesseract_cmd = str(candidate)
                break
    try:
        pytesseract.get_tesseract_version()
    except Exception:
        raise RuntimeError("Tesseract OCR is not installed or cannot be found. Install Tesseract, then run PDF2Word Pro again.")

    pdf=fitz.open(src); doc=Document()
    for i,page in enumerate(pdf):
        pix=page.get_pixmap(matrix=fitz.Matrix(2,2),alpha=False)
        img=Image.open(io.BytesIO(pix.tobytes("png")))
        text=pytesseract.image_to_string(img).strip()
        for para in text.split("\n\n"):
            if para.strip(): doc.add_paragraph(para.strip())
        if i<len(pdf)-1: doc.add_page_break()
    doc.save(dst); pdf.close()
