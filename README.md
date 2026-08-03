# AffectLab

AffectLab is a text-first research prototype for emotion-aware coaching and adaptive social rehearsal. It is not a therapist, medical service, or diagnostic system.

## Complete MVP

- Email/password accounts with Argon2 hashing, access JWTs, and rotating refresh cookies
- Ownership-protected MongoDB sessions with 30-day inactivity expiry and explicit deletion
- Rule-based affect tracking and strategy selection behind replaceable interfaces
- Optional OpenAI Responses API generation with moderation and transparent offline fallback
- Workload, personal-boundary, and relationship-need role-plays at three difficulty levels
- Pause, resume, manual completion, automatic success, and safety interruption
- Evidence-backed feedback with optional structured LLM wording
- Consent disclosure, responsive authenticated frontend, and account/session controls

## Run with Docker

Requirements: Docker Desktop with Compose.

```powershell
Copy-Item .env.example .env
# Set a long random JWT_SECRET and optionally OPENAI_API_KEY in .env
docker compose up --build
```

Open `http://localhost:5173`. MongoDB data is kept in the `mongodb_data` volume. The API and interactive documentation are available at `http://localhost:8000` and `http://localhost:8000/docs`.

## Run services locally

Start MongoDB on `localhost:27017`, then:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
$env:PERSISTENCE_BACKEND = "mongo"
$env:JWT_SECRET = "replace-this-with-at-least-32-random-bytes"
..\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

When `OPENAI_API_KEY` is absent or an API call fails, the backend uses its deterministic template generator. `OPENAI_MODEL` defaults to `gpt-5.6` and is configurable.

## Verify

```powershell
cd backend
..\.venv\Scripts\python.exe -m pytest
..\.venv\Scripts\python.exe -m ruff check .

cd ..\frontend
npm run lint
npm run build

cd ..
docker compose config
```

Tests use an in-memory repository adapter and never require live MongoDB or OpenAI access. Docker and normal configured deployments use the async PyMongo repository.

## Privacy and safety

Users must accept disclosure that text is stored locally for up to 30 days and that the full session may be sent to OpenAI when configured. Raw prompts and responses are not written to application logs. Crisis phrase checks run before response generation; provider moderation is secondary. The safety layer is a conservative prototype and requires independent evaluation before any study or public deployment.

See [docs/architecture.md](docs/architecture.md) for data flow and extension boundaries.

