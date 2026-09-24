from io import BytesIO
import base64
from pathlib import Path
import fitz
from docx import Document
from PIL import Image, ImageOps
import re


def _clean(text: str) -> str:
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _prepare_image(raw: bytes):
    """Normalize images for vision: readable resolution and safely below Groq's 20MB limit."""
    img = Image.open(BytesIO(raw))
    img = ImageOps.exif_transpose(img).convert("RGB")

    # Keep enough resolution for OCR while avoiding oversized data URLs.
    max_dim = 1800
    if max(img.size) > max_dim:
        scale = max_dim / max(img.size)
        img = img.resize((max(1, int(img.width * scale)), max(1, int(img.height * scale))), Image.Resampling.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90, optimize=True)
    encoded = base64.b64encode(buf.getvalue()).decode("ascii")
    data_url = f"data:image/jpeg;base64,{encoded}"
    return img, data_url, len(buf.getvalue())


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
        img, data_url, encoded_size = _prepare_image(raw)
        return (
            f"[IMAGE SOURCE]\nFilename: {filename}\nDimensions: {img.width}x{img.height}",
            {"type": "image", "width": img.width, "height": img.height, "prepared_bytes": encoded_size},
            data_url,
        )

    raise ValueError("Unsupported file format.")
