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
- AI: Groq API (optional; demo mode works without an API key)
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
