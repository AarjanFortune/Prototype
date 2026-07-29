# Guitarica

Guitarica is a full-stack guitar transcription application. It accepts uploaded
audio, single YouTube video links, or live microphone input and returns
synchronized tablature with timing metadata.

## Stack

- Frontend: React, TypeScript, Vite
- Backend: FastAPI, PyTorch, librosa, yt-dlp
- Runtime: Python 3.10+, Node.js 18+, FFmpeg

## Quick Start

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at `http://localhost:5173`. Backend runs at
`http://localhost:8000`.

## Essential Docs

- [ARCHITECTURE.md](ARCHITECTURE.md)
- [DEVELOPMENT.md](DEVELOPMENT.md)
- [DEPLOYMENT.md](DEPLOYMENT.md)
- [API.md](API.md)
