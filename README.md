# ContentForge AI

An AI-powered content transformation engine for SIH 2026.

## What it does

Upload a TXT, PDF, DOCX, or image, choose one or more output artefacts, set audience/tone/language/detail, and generate:

- LinkedIn Post
- X/Twitter Thread
- Advisory
- Executive Summary
- Presentation outline
- Infographic content
- Video package (script, storyboard, narration, subtitles, visual recommendations)

The system creates one normalized source context first and then generates all selected artefacts from that same context.

## Stack

- Frontend: React + Vite
- Backend: FastAPI
- AI: Groq API with Qwen 3.8 27B for text + image understanding (optional; demo mode works without an API key)
- Document parsing: PyMuPDF + python-docx
- PPTX export: python-pptx

## Run locally

### 1. Backend

```bash
cd backend
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

For PowerShell use:
```powershell
Copy-Item .env.example .env
```

Set `GROQ_API_KEY` in `.env` for real AI generation. If it is empty, the application automatically uses deterministic demo generation, so the complete UI can still be demonstrated.

### 2. Frontend

Open a second terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite, normally `http://localhost:5173`.

## API

- `GET /api/health`
- `POST /api/transform`
- `POST /api/export/pptx`

## Notes

The project intentionally does not hard-code any secret API key. Never commit your real `.env` file.

For production, add authentication, persistent storage, rate limiting, background jobs, and an external object store.


## Image input
PNG/JPG/WEBP uploads are sent as actual image data to the Groq multimodal model for visual understanding/OCR. The filename and dimensions are not used as the source content.

Production model:
```env
GROQ_MODEL=qwen/qwen3.8-27b
```

## v3 Source Intelligence Pipeline

The AI flow is now two-stage:
1. Source Intelligence: extracts facts and visual context from the source/image.
2. Transformation Engine: generates all selected artefacts from that shared verified brief.

This avoids generating each output directly from a filename/metadata placeholder and makes the architecture easier to explain during evaluation.


## v4 reliability fixes
- Uses Groq's documented multimodal chat endpoint directly for predictable vision requests.
- Normalizes uploaded images and keeps them below the documented 20 MB vision limit.
- Separates image metadata from actual visual content.
- Removes silent demo fallback when a Groq key exists; API errors are surfaced to the UI.
- Uses the shared Source Intelligence brief as the factual input to the transformation stage.
- Frontend API URL is controlled by `VITE_API_URL`.
