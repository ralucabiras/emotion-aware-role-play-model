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

## Validation-fitted deployment calibration

For each fold, the frozen models were run on that fold's validation session. A text weight was selected on a fixed 0.00–1.00 grid in increments of 0.01, then a final temperature was fitted by validation negative log-likelihood. Both parameters were frozen before evaluation on the held-out test session.

| Fold | Text weight | Audio weight | Temperature |
| --- | ---: | ---: | ---: |
| 1 | 0.62 | 0.38 | 0.6380 |
| 2 | 0.54 | 0.46 | 0.5959 |
| 3 | 0.63 | 0.37 | 0.6542 |
| 4 | 0.58 | 0.42 | 0.5738 |
| 5 | 0.57 | 0.43 | 0.5442 |

| Metric | Equal fusion | Validation-fitted fusion | Change |
| --- | ---: | ---: | ---: |
| Accuracy | 0.7832 | 0.7717 | -0.0116 |
| Macro F1 | 0.7883 | 0.7758 | -0.0126 |
| Weighted F1 | 0.7815 | 0.7707 | -0.0107 |
| ECE | 0.1619 | 0.0283 | -0.1336 |

Validation-fitted per-class F1 was 0.7951 for anger, 0.8221 for happiness, 0.6897 for neutral, and 0.7961 for sadness. The consistent text weights (0.54–0.63) support a text-dominant but genuinely multimodal combination. Calibration error fell by 82.5% relative to equal fusion, at a 0.0126 absolute macro-F1 cost.

The equal-weight result remains the predeclared confirmatory comparison for the hypothesis that audio adds information beyond contextual text. The validation-fitted result is the preferred operational configuration whenever confidence is exposed or used for thresholding. This distinction avoids selecting a scientific headline or deployment configuration from test-set performance after the fact.

## Global out-of-fold deployment calibrator

An initial pooled analysis of the 5,531 unique out-of-fold validation predictions yielded text weight 0.59, audio weight 0.41, and fusion temperature 0.6009347778. Its metrics are retained below as an intermediate result. It still consumed modality probabilities produced with fold-specific temperatures, so it is not by itself the final deployment recipe. The final global pass additionally fits one text temperature and one audio temperature from pooled raw validation logits before fitting fusion.

| Metric | Global OOF calibrator |
| --- | ---: |
| Accuracy | 0.7742 |
| Macro F1 | 0.7783 |
| Weighted F1 | 0.7732 |
| ECE | 0.0319 |
| NLL | 0.6059 |
| Multiclass Brier | 0.3269 |

The intermediate global calibrator slightly improves accuracy and macro F1 over fold-specific calibration while retaining low ECE. Its per-class F1 is 0.7984 for anger, 0.8228 for happiness, 0.6927 for neutral, and 0.7995 for sadness. Selection for the final full-data inference package requires the complete global modality-plus-fusion calibration chain; neither deployment analysis replaces the equal-weight confirmatory research comparison.

### Final global calibration chain

Fitting modality temperatures from pooled raw out-of-fold validation logits, followed by fusion fitting, produced the final deployment recipe:

- Text temperature: 1.8268186503
- Audio temperature: 1.3357223831
- Text weight: 0.59
- Audio weight: 0.41
- Fusion temperature: 0.5989429433
- Calibration examples: 5,531 unique out-of-fold validation predictions

Applied to the held-out fold predictions, the complete chain gives accuracy 0.7736, macro F1 0.7776, weighted F1 0.7728, ECE 0.0242, NLL 0.6075, and multiclass Brier score 0.3280. Per-class F1 is 0.7993 for anger, 0.8235 for happiness, 0.6936 for neutral, and 0.7942 for sadness. These are the parameters selected for full-data model packaging.

The paired context values above are reconstructed from the exact row-level artifacts used in fusion. They can differ slightly from an earlier run summary if nondeterministic GPU reruns overwrote the private fold artifacts; the paired analysis verifies every prediction file against its adjacent recorded fold metrics.

## Private artifacts

- Audio runs: `gs://affectlab-research-raluca-biras/runs/iemocap-audio/iemocap_benchmark4_audio_wav2vec2_base/`
- Fusion report: `gs://affectlab-research-raluca-biras/runs/iemocap-fusion/iemocap_benchmark4_context3_audio_equal_fusion/`
- Validation-fitted fusion: `gs://affectlab-research-raluca-biras/runs/iemocap-fusion/iemocap_benchmark4_validation_fitted_fusion/`
- Global OOF calibrator: `gs://affectlab-research-raluca-biras/runs/iemocap-fusion/iemocap_benchmark4_global_oof_calibrated_fusion/`
- Final full-data inference artifacts: `gs://affectlab-research-raluca-biras/models/iemocap-benchmark4-final-v1/` (text: 7 epochs; audio: 10 epochs; 5,531 unique examples each). These artifacts have no held-out score of their own; use the cross-validation results above for performance claims.
