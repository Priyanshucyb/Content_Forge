from io import BytesIO
import base64
from pathlib import Path
import fitz
from docx import Document
from PIL import Image
import re


def _clean(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_source(raw: bytes, filename: str):
    suffix = Path(filename).suffix.lower()

    if suffix in {".txt", ".md"}:
        text = raw.decode("utf-8", errors="replace")
        return _clean(text), {"type": "text", "chars": len(text)}, None

    if suffix == ".pdf":
        doc = fitz.open(stream=raw, filetype="pdf")
        pages = []
        for i, page in enumerate(doc):
            txt = page.get_text("text")
            if txt.strip():
                pages.append(f"[Page {i+1}]\n{txt}")
        text = "\n\n".join(pages)
        return _clean(text), {"type": "pdf", "pages": len(doc), "chars": len(text)}, None

    if suffix == ".docx":
        doc = Document(BytesIO(raw))
        chunks = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(chunks)
        return _clean(text), {"type": "docx", "paragraphs": len(chunks), "chars": len(text)}, None

    if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
        # The image itself is preserved as metadata, but OCR is intentionally
        # handled by the AI provider only when an API key is configured.
        img = Image.open(BytesIO(raw))
        mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp"}[suffix]
        data_url = f"data:{mime};base64,{base64.b64encode(raw).decode('ascii')}"
        return (
            f"[IMAGE SOURCE]\nThe uploaded image is the primary source. Filename: {filename}\n"
            f"Dimensions: {img.width}x{img.height}",
            {"type": "image", "width": img.width, "height": img.height},
            data_url,
        )

    raise ValueError("Unsupported file format.")
