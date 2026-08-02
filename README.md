# AffectLab

AffectLab is a research prototype for emotion-aware coaching and adaptive social rehearsal. It is designed to help people reflect on difficult social situations and practise conversations; it is **not** a therapist, medical service, or diagnostic tool.

The current milestone is a text-first full-stack baseline:

- React + TypeScript chat interface
- FastAPI API with typed domain models
- In-memory sessions and conversation history
- Replaceable rule-based emotion analyser and strategy selector
- Smoothed emotional state across turns
- One adaptive workload-conversation role-play
- Crisis-language interruption and delete-session endpoint

## Quick start

Requirements: Python 3.11+ and Node.js 20+.

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`; interactive documentation is at `http://localhost:8000/docs`.

### Frontend

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

Alternatively, run `docker compose up --build` from the repository root.

## Verify

```powershell
cd backend
pytest
ruff check .

cd ..\frontend
npm run lint
npm run build
```

## Architecture

The browser calls a small typed API. A conversation passes through emotion analysis, state smoothing, cognitive assessment, strategy selection, and response generation. Each intelligent component is behind a service boundary so a trained model or external LLM can replace the offline baseline without changing API routes.

Session storage is intentionally in memory for this milestone; restarting the backend clears it. Raw audio and video are not accepted or stored. See [docs/architecture.md](docs/architecture.md) for the module map and next steps.

## Safety scope

The prototype expresses affect estimates as uncertain signals, never diagnoses, and interrupts ordinary coaching when its conservative phrase matcher detects crisis-related language. The matcher is only a baseline and must be independently evaluated before any user study or public deployment.

