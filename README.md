# AffectLab

AffectLab is a text-first research prototype for emotion-aware coaching and adaptive social rehearsal. It is not a therapist, medical service, or diagnostic system.

## Complete MVP

- Email/password accounts with email confirmation, Argon2 hashing, access JWTs, and rotating refresh cookies
- Ownership-protected MongoDB sessions with 30-day inactivity expiry and explicit deletion
- Rule-based affect tracking and strategy selection behind replaceable interfaces
- Optional OpenAI Responses API generation with moderation and transparent offline fallback
- Workload, personal-boundary, and relationship-need role-plays at three difficulty levels
- Pause, resume, manual completion, automatic success, and safety interruption
- Evidence-backed feedback with optional structured LLM wording
- Adaptive OpenAI role-play wording constrained by deterministic dialogue actions, safety rules, and local fallback
- Guided first-run onboarding with explicit model/privacy boundaries and one-to-three persistent personal practice goals
- Authenticated home dashboard with automatic/editable session titles, resumable activity, and evidence-based rehearsal history
- Account-owned custom scenarios with constrained observable skills, plus one-exchange rewind and editable retry controls
- Same-scenario comparative feedback with stored metric provenance and user-authored takeaways surfaced on the dashboard
- Accessible busy/error announcements, keyboard focus treatments, reduced-motion support, and touch-oriented mobile workspace layouts
- Allowlisted researcher dashboard, access-code pilot enrollment, pseudonymous aggregate monitoring, and text-free CSV export
- Pseudonymous research events, versioned consent, pre/post ratings, and text-free personal data export
- Auditable text-intelligence baselines for emotion, cognitive patterns, intent, readiness, and resistance
- Scored strategy decisions with machine-readable reasons and model-version metadata
- Consent disclosure, responsive authenticated frontend, and account/session controls
- Profile and privacy settings with current-password-verified password changes

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

### Full-stack smoke test

The opt-in smoke suite builds and starts the production frontend, FastAPI backend, and MongoDB; seeds a verified demo researcher; exercises the core participant and research journey; restarts the backend; and removes its isolated containers and volume afterward.

```powershell
cd frontend
npm install
npx playwright install chromium
npm run test:e2e:full-stack
```

Use `npm run test:e2e:full-stack:attached` only when the smoke Compose stack is already running. The regular `npm run test:e2e` command remains the fast, backend-mocked browser suite.

## Email confirmation

New accounts must confirm their email address before signing in. Configure the SMTP settings in the repository `.env`; for Gmail on port 587, `SMTP_USE_TLS=true` and `SMTP_PASSWORD` must be a Google App Password, not the account's normal password. Google App Passwords require 2-Step Verification on the sender account. Keep the password only in `.env` and restart the backend after changing it.

Confirmation links use `FRONTEND_ORIGIN` (normally `http://localhost:5173`) and expire after `EMAIL_VERIFICATION_HOURS` (24 by default). Resending a confirmation invalidates the previous link. Responses from the resend endpoint are deliberately generic so they do not reveal whether an email is registered. Existing MongoDB accounts created before this feature can use the resend-confirmation action to become verified.

The frontend provides public routes for the landing page (`/`), About (`/about`), sign in (`/login`), sign up (`/signup`), email confirmation, and single-use password recovery. After first sign-in, `/onboarding` explains the research boundaries, optional voice processing, and asks the user to select personal practice goals before opening the authenticated workspace at `/app`.

Authenticated users can open `/settings` to update their name, country, timezone, and personal practice goals; control the local microphone preference; review or delete individual sessions; change their password; or delete the account. Password changes require the current password, revoke every refresh token, clear the refresh cookie, and sign the current browser out. Email changes remain deferred because they require a dedicated reconfirmation flow.

## Pilot study and researcher access

The frozen pilot protocol is [docs/study-protocol-v1.0.md](docs/study-protocol-v1.0.md), with a machine-readable companion at [configs/study_protocol_v1.json](configs/study_protocol_v1.json). The application records `STUDY_PROTOCOL_VERSION` in consent, durable study records, participant exports, researcher dashboards, and CSV rows. Any material post-recruitment change requires a new protocol and consent version rather than editing the frozen files.

Set `PILOT_ACCESS_CODE` to the code supplied to pilot participants, `PILOT_STUDY_LABEL` to the study display name, and `RESEARCHER_EMAILS` to a comma-separated allowlist of confirmed researcher accounts. Configure `STUDY_CONSENT_VERSION`, the retention statement, and the researcher, supervisor, and institution contact fields before inviting anyone. Restart the backend after changing these values. Participants review the server-provided participant information sheet in Settings and must separately affirm that they read it, voluntarily agree to participate, and accept the described data processing. The exact version and acceptance timestamp are stored with their account. Changing `STUDY_CONSENT_VERSION` requires participants to review and consent again before they appear as enrolled or in research exports.

The researcher dashboard and CSV export deliberately exclude names, email addresses, passwords, conversation text, audio, custom scenario wording, and saved takeaways. CSV rows contain pseudonymous participant/session identifiers, timestamps, turn counts, scenario identifiers, difficulty, completion reason, and questionnaire ratings. Keep `PILOT_ACCESS_CODE` and the researcher allowlist private; neither replaces normal account authentication.

Enrolled participants can withdraw from the study in Settings without deleting their AffectLab account. Withdrawal is timestamped, immediately excludes the participant from future researcher dashboards and CSV exports, and deletes study questionnaires and research-event telemetry still held in active sessions. Ordinary conversations, feedback, and takeaways remain available to the account holder. The interface explains that data already irreversibly anonymised or included in completed aggregate analysis may no longer be identifiable and therefore may not be removable. Re-enrollment is intentionally blocked after withdrawal.

Research analysis data is stored separately in the `study_records` collection and does not inherit the 30-day session expiry. Set `STUDY_RECORD_RETENTION_DAYS` and keep the participant-facing `STUDY_RETENTION_PERIOD` statement consistent with the approved protocol. MongoDB applies a TTL index to `retention_expires_at`. Each activity refreshes that explicit deadline. Records contain pseudonymous participant/session identifiers, consent version, timestamps, turn counts, scenario and completion fields, numeric feedback metrics, questionnaire ratings, generation source, and text-free event properties. They exclude names, email, conversation text, audio, custom scenario wording, feedback prose, and takeaways. Active post-consent session data is safely projected into this collection at startup; pre-consent events and questionnaire responses are not copied.

The researcher dashboard controls protocol start/end dates and participant analysis status. Researchers can record text-limited data-quality notes and a required reason when excluding a participant; withdrawn and excluded participants remain visible as lifecycle rows but are omitted from aggregate analysis and exports. When the study end date has been reached, **Freeze final dataset** creates a one-way `affectlab-frozen-dataset-v1` CSV snapshot. The snapshot uses new sequential analysis IDs with no stored account lookup and records its UTC timestamp, protocol/schema versions, participant count, record count, and SHA-256 checksum. Once frozen, the application blocks enrollment, durable study-record updates, date changes, and participant-review edits for that protocol. The CSV endpoint subsequently serves the immutable frozen snapshot and checksum. Participant withdrawal remains available because it is a data-subject right; it deletes identifiable live study records but cannot identify rows already irreversibly de-identified in the frozen snapshot.

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
npm run test:e2e

cd ..
docker compose config
```

The normal backend suite uses an in-memory repository and the Playwright suite uses a deterministic API boundary, so neither requires OpenAI or a mail service. Playwright runs the journeys in desktop and mobile Chromium and applies automated WCAG A/AA checks to representative screens. Install its browser once with `npx playwright install chromium`.

Real MongoDB persistence checks are deliberately opt-in and always create a uniquely named disposable database. With the local MongoDB service running:

```powershell
cd backend
$env:TEST_MONGODB_URI = "mongodb://localhost:27017"
..\.venv\Scripts\python.exe -m pytest -m mongo_integration -v
Remove-Item Env:TEST_MONGODB_URI
```

These checks cover client restart persistence, TTL index and logical expiry behavior, account cascade deletion, and optimistic concurrency protection. Never point `TEST_MONGODB_URI` at a server where the test account cannot safely create and drop `affectlab_integration_*` databases.

Run the bundled evaluation smoke dataset with:

```powershell
.venv\Scripts\python.exe ml\evaluation\evaluate_text.py ml\evaluation\sample_text_eval.jsonl
```

The evaluator reports accuracy, macro F1, per-class precision/recall/F1, mean confidence error, distortion accuracy, and individual predictions. The bundled rows are pipeline fixtures—not a scientific benchmark. Replace them with appropriately licensed, independently reviewed evaluation data before reporting results.

## Privacy and safety

Remote participant deployment has a separate mandatory security and safety baseline covering HTTPS, host/CORS restrictions, rate limits, backup restoration, dependency scanning, eligibility, and emergency limitations: [Remote pilot security baseline](docs/remote-pilot-security.md).

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

The backend exposes optional authenticated inference at `POST /api/affect/multimodal`. It is disabled by default, accepts base64-encoded WAV audio, derives causal context from the owned session, and never persists audio. Install `backend/requirements-inference.txt`, synchronize the private artifacts with `scripts/sync_final_models.ps1 -Destination <private-local-directory>`, then configure the `MULTIMODAL_*` environment variables from `.env.example`. Crisis and safety decisions remain text-first and do not depend on the trained model.

Multimodal responses expose calibrated text-only, audio-only, and fused distributions, plus agreement, latency, queue time, and confidence-level metadata. The UI does not headline a fused label below `MULTIMODAL_LOW_CONFIDENCE_THRESHOLD` (0.55 by default). This is a presentation abstention policy rather than a modification to the frozen model or its probabilities. Inference is serialized per backend process to prevent simultaneous requests from competing for model memory.

When that endpoint is enabled and its artifacts are available, the authenticated frontend shows an optional **Add voice** control. The browser records at most 20 seconds, converts the sample to mono 16 kHz PCM WAV, sends it only with the typed transcript for the current inference request, and then discards it. Microphone denial, an unavailable model, or an inference error leaves the normal text conversation usable. Browser microphone capture works on `localhost`; non-local deployments require HTTPS.

With `TRANSCRIPTION_ENABLED=true` and `OPENAI_API_KEY` configured, stopping a recording sends that transient WAV to OpenAI file transcription using the environment-selected `OPENAI_TRANSCRIPTION_MODEL` (`gpt-transcribe` by default). The returned transcript is placed in the composer for explicit review and editing; it is never sent as a chat turn until the user presses Send. AffectLab does not persist the raw recording. The implementation follows the [official OpenAI file transcription guide](https://developers.openai.com/api/docs/guides/speech-to-text).

The completed text results and dialogue-clustered paired bootstrap intervals are recorded in [docs/iemocap-text-results.md](docs/iemocap-text-results.md). Audio and calibrated fusion results are recorded in [docs/iemocap-multimodal-results.md](docs/iemocap-multimodal-results.md). Row-level reports remain in the private Cloud Storage experiment directories.

Enrollment also requires four separate eligibility confirmations: minimum age, approved geography, study language, and the additional frozen protocol inclusion/exclusion criteria displayed in Settings. Only the eligibility version, protocol version, and server timestamp are stored; no birth date, precise location, health details, or ineligibility reasons are collected. The eligibility version fingerprints the criteria and configured scope, so changed criteria and legacy accounts require confirmation before current enrollment and research collection/export.
