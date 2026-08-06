# Dataset registry

This registry records access and redistribution constraints separately from implementation code. It is not legal advice; verify terms again before publishing data, checkpoints, or derived artifacts.

| Dataset | Intended AffectLab use | Access | Recorded terms | Status |
| --- | --- | --- | --- | --- |
| MELD | First text-emotion benchmark; later audio/video comparison | Official public CSV annotations | Hugging Face dataset card identifies GPL-3.0; underlying dialogue derives from *Friends*, so do not redistribute raw media from this project | Approved for local dissertation experiment |
| IEMOCAP | Speech, text, and multimodal experiments | Individual USC application using academic email | Internal research only; non-transferable; non-commercial; no redistribution; consult USC before public performance comparisons | Access granted; approved for private dissertation experiments |
| ESConv | Support-strategy selection | Official repository | Academic research use only | Deferred until emotion baseline is complete |
| EmpatheticDialogues | Empathy-oriented comparison/fallback | Official repository | Review repository license before each use/export | Deferred |

## MELD provenance

- Project: <https://github.com/declare-lab/MELD>
- Dataset card: <https://huggingface.co/datasets/declare-lab/MELD>
- Paper: Poria et al., “MELD: A Multimodal Multi-Party Dataset for Emotion Recognition in Conversations”
- Files used by the text adapter: official `train_sent_emo.csv`, `dev_sent_emo.csv`, and `test_sent_emo.csv`
- Splits are retained exactly; `Dialogue_ID` is split-local, so leakage checks compare complete dialogue-content hashes rather than raw numeric IDs.
- The official train/test splits contain one exact duplicate dialogue. It is retained for benchmark comparability and recorded in the generated manifest.

## IEMOCAP provenance

- Release: `IEMOCAP_full_release.tar.gz`, obtained through the user's approved USC access.
- Private source object: `gs://affectlab-research-raluca-biras/data/raw/iemocap/IEMOCAP_full_release.tar.gz`.
- Verified size: 17,695,884,032 bytes.
- Verified local SHA-256: `B4A1EBD19655E54B5DE3F4FF60757EA0F9C0C8C76D50F6B2FEBDBF79F2BC69B1`.
- Cloud object generation: `1785934282898479`; composite-object CRC32C: `Lw4YJg==`.
- Five folds are speaker-independent. Each fold holds out one complete session for testing and the preceding session (cyclically) for validation.
- `benchmark_4` provides anger, happiness (including excitement), neutral, and sadness.
- `affectlab_6` provides anger, anxiety (IEMOCAP fear), frustration, joy (happiness and excitement), neutral, and sadness.

## Handling rules

- Keep raw and processed data outside Git and OneDrive-backed repository paths.
- Never commit credentials, downloaded media, cached Arrow files, or model checkpoints.
- Store source URLs, dataset fingerprints, label counts, and configuration with every run.
- Do not train on AffectLab user sessions without separate research consent and applicable ethics approval.
