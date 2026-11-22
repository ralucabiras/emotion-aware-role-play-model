# Reproduction and demonstration

## Reproduction

The Colab notebooks in `ml/notebooks` cover preprocessing, context text training, audio training, calibration, fusion, and final full-data packaging. Use only the authorized private IEMOCAP archive. Dataset rules are frozen in `docs/dataset-registry.md`; parameters are frozen in `configs/iemocap_final_multimodal.json`. Run folds by IEMOCAP session, fit every calibration/fusion parameter on validation predictions, and reserve the held-out session for evaluation.

The [model-file manifest captured on 22 November 2026](generated/model-provenance-v1.json) identifies the available final text and audio files. After downloading another copy of those model directories, capture a separate manifest for comparison:

```powershell
.venv\Scripts\python.exe scripts\capture_model_provenance.py --text-model "D:\models\text" --audio-model "D:\models\audio" --output ".local\model-provenance.json"
```

Compare each model's relative file list, byte counts, individual hashes, aggregate hash, and the configuration digest with the archived manifest. Capture timestamps, revisions, and local environments can differ between captures. Preserve the archived manifest as the baseline. Keep any new manifest containing restricted paths or metadata in the private dissertation evidence rather than committing it. The archived manifest records relative model filenames and capture metadata only; the original training environment is documented separately in [results and provenance](results-and-provenance.md#exact-artifact-provenance).

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


## Integrated product demonstration

Use [engineering demonstration v1](engineering-demonstration.md) for the complete rehearsal, replay, branch, comparison and action-card walkthrough. Its native smoke runner uses an isolated real MongoDB database and restarts the actual backend process. The memory-backed interactive demo above is for presentation only and loses sessions on restart. Synthetic uncertainty fixtures demonstrate policy behavior; they are not new trained-model measurements.
