# Reproduction and demonstration

## Reproduction

The Colab notebooks in `ml/notebooks` cover preprocessing, context text training, audio training, calibration, fusion, and final full-data packaging. Use only the authorized private IEMOCAP archive. Dataset rules are frozen in `docs/dataset-registry.md`; parameters are frozen in `configs/iemocap_final_multimodal.json`. Run folds by IEMOCAP session, fit every calibration/fusion parameter on validation predictions, and reserve the held-out session for evaluation.

After downloading final model directories, capture hashes and environment metadata:

```powershell
.venv\Scripts\python.exe scripts\capture_model_provenance.py --text-model "D:\models\text" --audio-model "D:\models\audio" --output "docs\evidence-package\private-model-provenance.json"
```

Do not commit that generated private manifest if paths or metadata reveal restricted storage details; archive it with the dissertation evidence instead.

## Offline demonstration

Start the backend with the dedicated environment file, without changing the normal `.env`:

```powershell
cd backend
..\.venv\Scripts\python.exe -m uvicorn app.main:app --env-file ..\configs\offline-demo.env.example --port 8000
```

Start the frontend normally in a second terminal. Sign in with `demo@example.com` / `affectlab-offline-demo`. This development-only account is recreated in memory on backend restart. Reflection and role-play use deterministic templates; transcription and multimodal inference visibly remain unavailable. No OpenAI, SMTP, MongoDB, Google Cloud, or internet connection is required. Use `synthetic-demo.json` for fictional wording.

## Five-minute presentation runbook

1. Start both services and open `/login` before screen sharing.
2. Sign in with the offline demo account; state that the dataset is synthetic and network services are disabled.
3. Show one reflection exchange, then start the workload role-play.
4. Use the three synthetic turns, pause/resume once, finish, and show evidence-backed feedback and takeaway saving.
5. Show the history dashboard, consent boundary, and researcher dashboard screenshots rather than changing research state live.
6. Close on the canonical results table and the acted-English/four-class limitations.

Record a short backup video following exactly this route after the interface is frozen. Store the recording outside Git with the slide deck, tested on the presentation laptop. Also keep screenshots of login, role-play, feedback, history, consent, and researcher export as a no-video fallback.
