@echo off
echo Starting ContentForge AI backend...
start "ContentForge Backend" cmd /k "cd backend && python -m venv .venv 2>nul && call .venv\Scripts\activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8000"
timeout /t 3 >nul
echo Starting ContentForge AI frontend...
start "ContentForge Frontend" cmd /k "cd frontend && npm install && npm run dev"
echo.
echo Two terminals were opened. Use the Vite URL shown in the frontend terminal.
