# Model card: IEMOCAP multimodal research models

## Models

| Component | Base model | Input | Output |
| --- | --- | --- | --- |
| Context text | `microsoft/deberta-v3-small` | Target utterance plus three previous causal turns and speaker markers | anger, happiness, neutral, sadness |
| Audio | `facebook/wav2vec2-base` | Mono 16 kHz speech, maximum 20 seconds | same four classes |
| Late fusion | No additional encoder | Calibrated text and audio posterior vectors | same four classes plus calibrated confidence |

The final full-data text model used 7 epochs and the audio model 10 epochs over 5,531 examples, seed 42. Their training runs are packaging runs, not independent evaluations. Report performance only from the five speaker-independent cross-validation folds.

The operational fusion recipe is text temperature 1.8268186503, audio temperature 1.3357223831, text/audio weights 0.59/0.41, then fusion temperature 0.5989429433. The checked-in source is `configs/iemocap_final_multimodal.json`.

## Intended use

Exploratory affect signals that can adjust the pacing and presentation of an English-language conversation-practice prototype. Predictions must be presented as uncertain research estimates and must never override user self-report or deterministic crisis handling.

## Data and generalization limitations

IEMOCAP is a relatively small corpus of acted and improvised English dyadic interactions recorded in controlled sessions. Its speakers, recording conditions, conversational tasks, and emotional performances do not represent everyday participants or deployment microphones. Session-held-out evaluation reduces speaker leakage but does not establish generalization across cultures, accents, ages, disabilities, devices, environments, spontaneous distress, or clinical populations.

The four-class task collapses excitement into happiness and excludes anxiety, frustration, fear, shame, guilt, mixed affect, and uncertainty. A forced label can therefore be semantically wrong even when the classifier is statistically correct under its benchmark mapping. Class performance is uneven, with neutral consistently weaker in fusion. Confidence calibration on IEMOCAP does not guarantee calibration in AffectLab conversations.

## Ethical and licensing constraints

IEMOCAP access is restricted. Do not redistribute its raw media, transcripts, row-level predictions, or derived examples. These models are not diagnostic devices and have not been clinically validated. A real pilot must analyze subgroup and failure patterns cautiously; IEMOCAP does not support strong demographic fairness conclusions.
