# Dataset registry

This registry records access and redistribution constraints separately from implementation code. It is not legal advice; verify terms again before publishing data, checkpoints, or derived artifacts.

| Dataset | Intended AffectLab use | Access | Recorded terms | Status |
| --- | --- | --- | --- | --- |
| MELD | First text-emotion benchmark; later audio/video comparison | Official public CSV annotations | Hugging Face dataset card identifies GPL-3.0; underlying dialogue derives from *Friends*, so do not redistribute raw media from this project | Approved for local dissertation experiment |
| IEMOCAP | Speech, text, and multimodal experiments | Individual USC application using academic email | Internal research only; non-transferable; non-commercial; no redistribution; consult USC before public performance comparisons | Access requested; no adapter execution until approved |
| ESConv | Support-strategy selection | Official repository | Academic research use only | Deferred until emotion baseline is complete |
| EmpatheticDialogues | Empathy-oriented comparison/fallback | Official repository | Review repository license before each use/export | Deferred |

## MELD provenance

- Project: <https://github.com/declare-lab/MELD>
- Dataset card: <https://huggingface.co/datasets/declare-lab/MELD>
- Paper: Poria et al., “MELD: A Multimodal Multi-Party Dataset for Emotion Recognition in Conversations”
- Files used by the text adapter: official `train_sent_emo.csv`, `dev_sent_emo.csv`, and `test_sent_emo.csv`
- Splits are retained exactly; `Dialogue_ID` is split-local, so leakage checks compare complete dialogue-content hashes rather than raw numeric IDs.

## Handling rules

- Keep raw and processed data outside Git and OneDrive-backed repository paths.
- Never commit credentials, downloaded media, cached Arrow files, or model checkpoints.
- Store source URLs, dataset fingerprints, label counts, and configuration with every run.
- Do not train on AffectLab user sessions without separate research consent and applicable ethics approval.
