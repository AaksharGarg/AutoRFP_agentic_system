# src/crawler/ocr_utils.py
from pdf2image import convert_from_path
import pytesseract
from pdfminer.high_level import extract_text as pdf_extract_text
import os

def extract_text_from_pdf_file(path: str, do_ocr_if_needed: bool = True) -> str:
    """
    First try pdfminer (text extraction). If result is short or empty and do_ocr_if_needed,
    render pages and run pytesseract OCR.
    """
    text = ""
    try:
        text = pdf_extract_text(path)
    except Exception:
        text = ""
    if text and len(text.strip()) > 200:
        return text
    if not do_ocr_if_needed:
        return text
    try:
        pages = convert_from_path(path, dpi=200)
    except Exception:
        return text
    result = []
    for page in pages:
        try:
            txt = pytesseract.image_to_string(page)
        except Exception:
            txt = ""
        if txt:
            result.append(txt)
    return "\n".join(result)
