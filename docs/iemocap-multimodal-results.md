# IEMOCAP audio and multimodal results

These are private, speaker-independent dissertation experiments on IEMOCAP. Raw data, row-level predictions, and model checkpoints must not be redistributed.

## Frozen design

- Task: four-class anger, happiness (including excitement), neutral, and sadness.
- Splits: five folds, each holding out one complete IEMOCAP session for testing and another for validation.
- Audio model: `facebook/wav2vec2-base`, frozen feature encoder, maximum duration 20 seconds.
- Calibration: one scalar temperature fitted separately on each fold's validation logits.
- Fusion: fixed 0.5 context-text plus 0.5 audio average of validation-calibrated posteriors.
- Statistical comparison: paired percentile bootstrap with 10,000 resamples over 151 complete dialogues, seed 20260808.
- The fusion weight was declared before examining the combined test result and was not optimized on test predictions.

## Audio-only baseline

| Metric | Pooled result |
| --- | ---: |
| Accuracy | 0.6279 |
| Macro F1 | 0.6349 |
| Weighted F1 | 0.6229 |
| Calibrated ECE | 0.0468 |

Audio-only per-class F1 was 0.7142 for anger, 0.5782 for happiness, 0.5757 for neutral, and 0.6715 for sadness. It is weaker than contextual text alone but supplies complementary signal.

## Equal-weight late fusion

| Metric | Context text | Fusion | Difference | Dialogue-bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Accuracy | 0.7304 | 0.7832 | +0.0528 | [+0.0381, +0.0683] |
| Macro F1 | 0.7332 | 0.7883 | +0.0551 | [+0.0407, +0.0713] |
| Weighted F1 | 0.7300 | 0.7815 | +0.0514 | [+0.0366, +0.0671] |

All 10,000 dialogue-bootstrap replicates favored fusion for each aggregate metric (smoothed probability of improvement 1.0). Fusion per-class F1 was 0.8277 for anger, 0.8163 for happiness, 0.7014 for neutral, and 0.8080 for sadness.

The fusion ECE is 0.1619. Classification improves strongly, but averaging two separately calibrated posterior vectors does not preserve calibration. Treat the fused scores as ranking/classification outputs until a fusion calibrator is fitted on paired validation predictions; do not present them as reliable probabilities.

The paired context values above are reconstructed from the exact row-level artifacts used in fusion. They can differ slightly from an earlier run summary if nondeterministic GPU reruns overwrote the private fold artifacts; the paired analysis verifies every prediction file against its adjacent recorded fold metrics.

## Private artifacts

- Audio runs: `gs://affectlab-research-raluca-biras/runs/iemocap-audio/iemocap_benchmark4_audio_wav2vec2_base/`
- Fusion report: `gs://affectlab-research-raluca-biras/runs/iemocap-fusion/iemocap_benchmark4_context3_audio_equal_fusion/`
