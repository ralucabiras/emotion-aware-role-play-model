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

The pooled held-out set contains 7,420 examples: 1,103 anger, 40 anxiety, 1,849 frustration, 1,636 joy, 1,708 neutral, and 1,084 sadness. Anxiety therefore accounts for only 0.54% of the exploratory dataset.

| Metric | Utterance baseline | Three-turn context | Difference | Dialogue-bootstrap 95% interval |
| --- | ---: | ---: | ---: | ---: |
| Accuracy | 0.5674 | 0.6228 | +0.0554 | [0.0382, 0.0734] |
| Macro F1 | 0.5490 | 0.6222 | +0.0732 | [0.0485, 0.1009] |
| Weighted F1 | 0.5675 | 0.6205 | +0.0529 | [0.0359, 0.0702] |

Macro F1 varied across the five held-out sessions as follows:

| Fold | Test n | Anxiety n | Utterance baseline | Three-turn context | Difference |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1,377 | 12 | 0.5690 | 0.6180 | +0.0490 |
| 2 | 1,357 | 9 | 0.5683 | 0.6655 | +0.0972 |
| 3 | 1,535 | 2 | 0.4992 | 0.5813 | +0.0820 |
| 4 | 1,519 | 7 | 0.5792 | 0.6268 | +0.0475 |
| 5 | 1,632 | 10 | 0.5122 | 0.5870 | +0.0748 |
| Mean ± SD | — | — | 0.5456 ± 0.0330 | 0.6157 ± 0.0304 | +0.0701 |

Context produced higher macro F1 in every fold. The fold-specific gains ranged from 0.0475 to 0.0972. The unweighted fold means differ slightly from the pooled values above, which are recomputed after concatenating all held-out predictions. The 2–12 anxiety examples in individual test sessions make class-specific fold estimates unstable.

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

For the context models, pooled calibrated ECE was 0.0311 on the four-class task and 0.0362 on the six-class task. Calibration changes confidence, not predicted labels or F1. Application confidence thresholds still require separate validation on AffectLab-like conversational data.

## Private aggregate reports

- `gs://affectlab-research-raluca-biras/runs/iemocap-text/comparisons/benchmark4_paired_bootstrap.json`
- `gs://affectlab-research-raluca-biras/runs/iemocap-text/comparisons/affectlab6_paired_bootstrap.json`
