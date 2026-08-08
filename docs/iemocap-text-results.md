# IEMOCAP text experiment results

These are internal dissertation results from the private, access-controlled IEMOCAP release. They are not evidence of clinical validity and must not be used to claim reliable recognition of a person's internal emotional state.

## Experimental design

- Model: `microsoft/deberta-v3-small`.
- Evaluation: five speaker-independent folds; each IEMOCAP session appears once as test data and a different complete session supplies validation data.
- Seed: 42.
- Baseline input: target utterance only.
- Context input: target utterance plus the previous three causal dialogue turns and same/other-speaker markers.
- Calibration: one scalar temperature fitted on validation logits only, then applied to the held-out test session.
- Statistical comparison: paired percentile bootstrap of 10,000 samples over 151 complete dialogues, seed 20260808. Baseline and context use identical sampled dialogue clusters in each replicate.

Small numerical differences from an earlier displayed context summary reflect later repeat executions of the same seeded GPU experiment. The comparison below uses the latest internally consistent Cloud Storage fold artifacts: every prediction file was verified against its accompanying `metrics.json` before resampling.

## Four-class benchmark

| Metric | Utterance baseline | Three-turn context | Difference | Dialogue-bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Accuracy | 0.6624 | 0.7304 | +0.0680 | [0.0496, 0.0864] |
| Macro F1 | 0.6651 | 0.7332 | +0.0681 | [0.0504, 0.0857] |
| Weighted F1 | 0.6640 | 0.7300 | +0.0661 | [0.0477, 0.0842] |

All three aggregate intervals exclude zero. Per-class F1 differences were:

| Class | Difference | Dialogue-bootstrap 95% interval |
| --- | ---: | ---: |
| Anger | +0.0198 | [-0.0073, 0.0449] |
| Happiness | +0.0882 | [0.0643, 0.1124] |
| Neutral | +0.0338 | [0.0060, 0.0602] |
| Sadness | +0.1307 | [0.0970, 0.1678] |

The anger interval includes zero; the data do not establish an anger-specific improvement even though the aggregate effect is clear.

## AffectLab-aligned six-class task

| Metric | Utterance baseline | Three-turn context | Difference | Dialogue-bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Accuracy | 0.5674 | 0.6228 | +0.0554 | [0.0382, 0.0734] |
| Macro F1 | 0.5490 | 0.6222 | +0.0732 | [0.0485, 0.1009] |
| Weighted F1 | 0.5675 | 0.6205 | +0.0529 | [0.0359, 0.0702] |

Per-class F1 differences were:

| Class | Difference | Dialogue-bootstrap 95% interval |
| --- | ---: | ---: |
| Anger | +0.0053 | [-0.0288, 0.0339] |
| Anxiety | +0.1650 | [0.0476, 0.3144] |
| Frustration | +0.0402 | [0.0158, 0.0647] |
| Joy | +0.1088 | [0.0804, 0.1371] |
| Neutral | -0.0033 | [-0.0316, 0.0241] |
| Sadness | +0.1232 | [0.0926, 0.1557] |

The anxiety estimate remains exploratory because IEMOCAP contains only 40 fear annotations; its wide interval reflects this limitation. The anger and neutral intervals include zero, so no class-specific improvement is established for those labels.

## Calibration

For the context models, pooled calibrated ECE was 0.0317 on the four-class task and 0.0362 on the six-class task. Calibration changes confidence, not predicted labels or F1. Application confidence thresholds still require separate validation on AffectLab-like conversational data.

## Private aggregate reports

- `gs://affectlab-research-raluca-biras/runs/iemocap-text/comparisons/benchmark4_paired_bootstrap.json`
- `gs://affectlab-research-raluca-biras/runs/iemocap-text/comparisons/affectlab6_paired_bootstrap.json`
