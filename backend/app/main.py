from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from pathlib import Path
from io import BytesIO
import os
import re
import json
import base64

from dotenv import load_dotenv
load_dotenv()

from .extractors import extract_source
from .generator import generate_outputs
from .pptx_export import build_pptx


app = FastAPI(
    title="ContentForge AI API",
    version="1.0.0",
    description="Multimodal content transformation engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TransformRequest(BaseModel):
    source_text: str = Field(min_length=1, max_length=100000)
    outputs: List[str] = Field(min_length=1)
    audience: str = "General"
    tone: str = "Professional"
    language: str = "English"
    detail: str = "Medium"
    objective: str = "Inform"
    style: str = "Clear and concise"


class TransformResponse(BaseModel):
    mode: str
    source: Dict[str, Any]
    outputs: Dict[str, Any]
    error: Optional[str] = None


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "ai_configured": bool(os.getenv("GROQ_API_KEY")),
        "model": os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
    }


@app.post("/api/transform", response_model=TransformResponse)
def transform(req: TransformRequest):
    try:
        result = generate_outputs(
            source_text=req.source_text,
            outputs=req.outputs,
            audience=req.audience,
            tone=req.tone,
            language=req.language,
            detail=req.detail,
            objective=req.objective,
            style=req.style,
        )
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/transform-upload", response_model=TransformResponse)
async def transform_upload(
    file: UploadFile = File(...),
    outputs: str = Form(...),
    audience: str = Form("General"),
    tone: str = Form("Professional"),
    language: str = Form("English"),
    detail: str = Form("Medium"),
    objective: str = Form("Inform"),
    style: str = Form("Clear and concise"),
):
    allowed = {
        ".txt", ".md", ".pdf", ".docx", ".png", ".jpg", ".jpeg", ".webp"
    }
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {suffix or 'unknown'}. Use TXT, MD, PDF, DOCX, PNG, JPG or WEBP."
        )

    raw = await file.read()
    try:
        source_text, meta, image_data_url = extract_source(raw, file.filename or "upload")
        if not source_text.strip():
            raise ValueError("No readable content was found in the uploaded file.")

        result = generate_outputs(
            source_text=source_text,
            outputs=json.loads(outputs),
            audience=audience,
            tone=tone,
            language=language,
            detail=detail,
            objective=objective,
            style=style,
            image_data_url=image_data_url,
        )
        result["source"]["filename"] = file.filename
        result["source"]["file_meta"] = meta
        return result
    except Exception as exc:
        raise HTTPException(status_code=502 if os.getenv("GROQ_API_KEY") else 400, detail=str(exc))


@app.post("/api/export/pptx")
def export_pptx(payload: Dict[str, Any]):
    try:
        outputs = payload.get("outputs", {})
        title = payload.get("title", "ContentForge AI Presentation")
        pptx_bytes = build_pptx(title, outputs)
        return StreamingResponse(
            BytesIO(pptx_bytes),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": 'attachment; filename="contentforge-presentation.pptx"'},
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
