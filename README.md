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
- Auditable text-intelligence baselines for emotion, cognitive patterns, intent, readiness, and resistance
- Scored strategy decisions with machine-readable reasons and model-version metadata
- Consent disclosure, responsive authenticated frontend, and account/session controls

## Run with an existing local MongoDB installation

Set `PERSISTENCE_BACKEND=mongo`, `MONGODB_URI=mongodb://localhost:27017`, `MONGODB_DATABASE=affectlab`, and a long random `JWT_SECRET` in `.env`. MongoDB Compass is optional administration software; the backend connects directly to the MongoDB service. Then use the local service commands below. Docker is not required.

## Run with Docker instead

Requirements: Docker Desktop with Compose. Use this option only when a local MongoDB service is not already available.

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

Run the bundled evaluation smoke dataset with:

```powershell
.venv\Scripts\python.exe ml\evaluation\evaluate_text.py ml\evaluation\sample_text_eval.jsonl
```

The evaluator reports accuracy, macro F1, per-class precision/recall/F1, mean confidence error, distortion accuracy, and individual predictions. The bundled rows are pipeline fixtures—not a scientific benchmark. Replace them with appropriately licensed, independently reviewed evaluation data before reporting results.

## Privacy and safety

Users must accept disclosure that text is stored locally for up to 30 days and that the full session may be sent to OpenAI when configured. Raw prompts and responses are not written to application logs. Crisis phrase checks run before response generation; provider moderation is secondary. The safety layer is a conservative prototype and requires independent evaluation before any study or public deployment.

See [docs/architecture.md](docs/architecture.md) for data flow and extension boundaries.

## Colab model training

The first transformer experiment uses MELD text with `microsoft/deberta-v3-small`. Open [the Colab notebook](ml/notebooks/affectlab_meld_training_colab.ipynb) in Google Colab, select a GPU runtime, add `HF_TOKEN` to Colab Secrets, and run the cells in order. Data, checkpoints, metrics, predictions, and confusion matrices are written to `MyDrive/AffectLab`, not the repository.

Run seed `42` first as a pipeline check. After it succeeds, set `RUN_ALL_SEEDS = True` and run the predeclared seeds `13`, `42`, and `73`. Report the aggregate rather than choosing the best test seed. Dataset provenance and restrictions are recorded in [docs/dataset-registry.md](docs/dataset-registry.md).

The private IEMOCAP workflow uses Google Cloud Storage rather than Drive. Its preprocessing notebook is retained for reproducibility, but the verified folds already exist at `gs://affectlab-research-raluca-biras/data/processed/iemocap-text-v1`. Open [the IEMOCAP text-training notebook](ml/notebooks/affectlab_iemocap_text_training_colab.ipynb), select a GPU, and run fold 5 first. Then set `RUN_ALL_FOLDS = True` and run all five speaker-independent folds. The four-class benchmark is primary; the class-balanced six-class AffectLab experiment is opt-in and must disclose that IEMOCAP contains only 40 fear annotations.

After preserving those baselines, use [the context and calibration notebook](ml/notebooks/affectlab_iemocap_context_calibration_colab.ipynb). It consumes the versioned private `iemocap-text-v2-context3` artifacts, compares three previous causal turns against the utterance-only baseline, and fits temperature scaling using validation logits only. Do not enable its six-class context run until the complete four-class ablation has been reviewed.

The next frozen comparison is the speaker-independent audio-only baseline. Open [the IEMOCAP audio-training notebook](ml/notebooks/affectlab_iemocap_audio_training_colab.ipynb), select an A100 or L4 GPU when available, and leave `RUN_ALL_AUDIO_FOLDS = False` for the first run. This trains only fold 5 with `facebook/wav2vec2-base`, a 20-second maximum waveform duration, a frozen feature encoder, and validation-only temperature scaling. Review that run before enabling all five folds. The notebook downloads the licensed audio bundle from the private Cloud Storage bucket, verifies its SHA-256 digest, and never writes audio into the repository.

Once all five audio folds are frozen, run [the calibrated late-fusion notebook](ml/notebooks/affectlab_iemocap_late_fusion_colab.ipynb) on a CPU runtime. It uses a predeclared equal-weight average of context-text and audio calibrated posteriors, verifies exact utterance pairing, and reports a paired dialogue-cluster bootstrap against context text. Do not tune the fusion weight on the held-out test predictions.

For deployable confidence estimates, use [the validation-fitted fusion calibration notebook](ml/notebooks/affectlab_iemocap_fusion_calibration_colab.ipynb). It reloads frozen checkpoints for validation inference only—without retraining—fits a modality weight and final temperature independently inside each fold, and then applies those parameters to the untouched test session.

After validation predictions exist, [the CPU-only calibration report notebook](ml/notebooks/affectlab_iemocap_calibration_report_colab.ipynb) reproduces the fit without checkpoints and stores calibrated row-level outputs, NLL, multiclass Brier score, ECE, and reliability bins. It also fits one global calibrator on pooled out-of-fold validation predictions, yielding the single modality weight and temperature required by a final full-data deployment model.

With the complete global modality-plus-fusion calibration chain frozen, [the final-model notebook](ml/notebooks/affectlab_iemocap_final_models_colab.ipynb) trains one context-text and one audio artifact on all 5,531 unique rows. It derives fixed epoch counts from the median completed cross-validation epochs and uploads the private artifacts under `models/iemocap-benchmark4-final-v1`. Training metrics from these full-data artifacts are not evaluation results.

The completed text results and dialogue-clustered paired bootstrap intervals are recorded in [docs/iemocap-text-results.md](docs/iemocap-text-results.md). Audio and calibrated fusion results are recorded in [docs/iemocap-multimodal-results.md](docs/iemocap-multimodal-results.md). Row-level reports remain in the private Cloud Storage experiment directories.
