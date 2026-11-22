# Supplementary model settings and results

This record preserves the detailed settings and aggregate tables removed from Appendix C when it was shortened on 22 November 2026. Values retain the recorded four-decimal precision; differences calculated before rounding need not equal subtraction of displayed scores. No training or evaluation was rerun for this editorial revision.

The [canonical results](results-and-provenance.md) distinguish independent held-out evaluation from label-reused packaging diagnostics. Dataset media, row-level predictions, and weights remain restricted; the tables here contain aggregate results only.

## Reproduction settings and archive references

The following settings identify the principal four-class experiments and the later full-data inference package. Only the rotating held-out-session models support performance claims. The historical evidence commit identifies the earlier archive snapshot; the model-file manifest linked below was captured later.

### Compact provenance for the principal IEMOCAP experiments and packaging run.

| Field | Frozen value |
| --- | --- |
| Model identifiers | `iemocap_benchmark4_deberta_v3_small` and `iemocap_benchmark4_context3_deberta_v3_small`, both `microsoft/deberta-v3-small`; `iemocap_benchmark4_audio_wav2vec2_base`, using `facebook/wav2vec2-base`; package `iemocap_benchmark4_final_multimodal`. |
| Seeds | Training and data order: 42. Paired dialogue bootstrap: 20260808, 10,000 replicates. |
| Session-role schedule | Test S1/validation S5/train S2–S4; test S2/validation S1/train S3–S5; test S3/validation S2/train S1,S4,S5; test S4/validation S3/train S1,S2,S5; test S5/validation S4/train S1–S3. |
| Optimisation | Recorded Transformers environment default `adamw_torch_fused` (fused PyTorch AdamW); text learning rate 2 × 10⁻⁵, audio 1 × 10⁻⁵; weight decay 0.01 and linear 10% warm-up for both. |
| Batching | Text train/evaluation batch 16/32, one accumulation step. Audio 4/8, four accumulation steps (effective training batch 16). |
| Epoch selection | Evaluation and checkpointing after each epoch; retain highest validation macro F1; maxima 8 text and 10 audio epochs, with early stopping after two non-improving evaluations. Full-data package counts were frozen from the completed experiment histories at 7 text and 10 audio epochs. |
| Input limits | Utterance-only text: 128 tokens. Three-turn causal context: 256 tokens. Audio: mono 16 kHz and at most 20 seconds; 16 of 5,531 files were truncated. |
| Calibration and fusion | Each scalar temperature minimises validation NLL by 80-step golden-section search over log T ∈ [-3, 3]. Confirmatory fusion fixes text/audio weights at 0.5/0.5. The calibration-oriented variant searches text weight 0.00–1.00 in 0.01 steps on each validation session, then fits a scalar fusion temperature before testing. |
| ECE definition | Maximum-probability ECE with 15 equal-width bins on [0,1]; bins use (l,u], and each absolute confidence–accuracy gap is weighted by its sample fraction. |
| Recorded environment | Final packaging manifests: Python 3.12.13; PyTorch 2.11.0+cu128; Transformers 5.13.1; mixed FP16 on an NVIDIA Tesla T4. Each restricted fold's metrics file separately records its run environment. |
| Revision and configuration | Preparation commit [0411ee550318e6031b5edccce13db74640e99d74](https://github.com/ralucabiras/emotion-aware-role-play-model/tree/0411ee550318e6031b5edccce13db74640e99d74); SHA-256 of `configs/iemocap_final_multimodal.json`: `d1a29a886293d5ed7398afc3208b4e866ef50d78b03b5792c5c66fb4693e0914`. |
| Evidence archive | Training code/configuration: the preparation commit linked above. Canonical repository evidence: [`docs/evidence-package` at commit `79ea347376537b781cdf6b4b5fa5311ae13ee838`](https://github.com/ralucabiras/emotion-aware-role-play-model/tree/79ea347376537b781cdf6b4b5fa5311ae13ee838/docs/evidence-package). Restricted reports and artefacts: `gs://affectlab-research-raluca-biras/runs/` and `gs://affectlab-research-raluca-biras/models/iemocap-benchmark4-final-v1/`. |

IEMOCAP media, row-level predictions, and weights cannot be redistributed, so access to the private evidence archive requires authorisation. On 22 November 2026, hashes for the nine locally available final-model files were recorded in [the completed manifest](generated/model-provenance-v1.json). It records file sizes, individual and aggregate SHA-256 digests, the configuration digest, and the capture revision and environment. The latter describe the local capture, not the original training run. These fingerprints identify the available full-data package; they do not retrospectively verify its training history or establish independent reproduction of the held-out experiments. See [exact artifact provenance](results-and-provenance.md#exact-artifact-provenance) for the aggregate digests and [reproduction instructions](reproduction-and-demo.md#reproduction) for comparison guidance.

## Four-class supporting results

Pooled class metrics are computed after concatenating the five non-overlapping held-out sessions. Fold means are unweighted descriptive summaries and therefore need not equal the pooled values. The dissertation retains the class F1 values in one heatmap and compares the five session scores in a point plot; the exact session values and full precision, recall, support, and fold summaries follow.

### Per-class results for the four-class text configurations.

| Configuration | Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- | --- |
| Utterance-only text | Anger | 0.7465 | 0.6863 | 0.7152 | 1,103 |
| Utterance-only text | Happiness | 0.7392 | 0.6980 | 0.7180 | 1,636 |
| Utterance-only text | Neutral | 0.6134 | 0.6001 | 0.6067 | 1,708 |
| Utterance-only text | Sadness | 0.5688 | 0.6827 | 0.6205 | 1,084 |
| Three-turn context | Anger | 0.7781 | 0.6963 | 0.7349 | 1,103 |
| Three-turn context | Happiness | 0.7989 | 0.8136 | 0.8062 | 1,636 |
| Three-turn context | Neutral | 0.6421 | 0.6388 | 0.6404 | 1,708 |
| Three-turn context | Sadness | 0.7209 | 0.7841 | 0.7512 | 1,084 |

### Per-class results for the audio and fusion configurations.

| Configuration | Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- | --- |
| Audio only | Anger | 0.6583 | 0.7806 | 0.7142 | 1,103 |
| Audio only | Happiness | 0.6343 | 0.5312 | 0.5782 | 1,636 |
| Audio only | Neutral | 0.6214 | 0.5363 | 0.5757 | 1,708 |
| Audio only | Sadness | 0.5997 | 0.7629 | 0.6715 | 1,084 |
| Equal-weight fusion | Anger | 0.8053 | 0.8513 | 0.8277 | 1,103 |
| Equal-weight fusion | Happiness | 0.8221 | 0.8105 | 0.8163 | 1,636 |
| Equal-weight fusion | Neutral | 0.7412 | 0.6657 | 0.7014 | 1,708 |
| Equal-weight fusion | Sadness | 0.7635 | 0.8579 | 0.8080 | 1,084 |
| Validation-fitted fusion | Anger | 0.8024 | 0.7879 | 0.7951 | 1,103 |
| Validation-fitted fusion | Happiness | 0.8208 | 0.8233 | 0.8221 | 1,636 |
| Validation-fitted fusion | Neutral | 0.7096 | 0.6710 | 0.6897 | 1,708 |
| Validation-fitted fusion | Sadness | 0.7601 | 0.8358 | 0.7961 | 1,084 |

### Macro F1 by held-out IEMOCAP session.

| Configuration | S1 | S2 | S3 | S4 | S5 | Mean | SD | Range |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Utterance-only text | 0.6376 | 0.7125 | 0.6443 | 0.6575 | 0.6625 | 0.6629 | 0.0264 | 0.6376–0.7125 |
| Three-turn context | 0.6918 | 0.7556 | 0.7235 | 0.7310 | 0.7505 | 0.7305 | 0.0227 | 0.6918–0.7556 |
| Audio only | 0.6450 | 0.6974 | 0.5870 | 0.6017 | 0.6224 | 0.6307 | 0.0386 | 0.5870–0.6974 |
| Equal-weight fusion | 0.7517 | 0.8108 | 0.7708 | 0.8090 | 0.7922 | 0.7869 | 0.0227 | 0.7517–0.8108 |
| Validation-fitted fusion | 0.7294 | 0.8070 | 0.7542 | 0.7932 | 0.7852 | 0.7738 | 0.0281 | 0.7294–0.8070 |

Context exceeded utterance-only text in all five sessions, and equal fusion produced the highest macro F1 in every session. Audio varied most across sessions. With only five actor dyads, these values show observed fold variation rather than population-level speaker variability.

## Exploratory six-class experiment

The exploratory mapping used anger, anxiety, frustration, joy, neutral, and sadness. Its five held-out sessions contained 7,420 examples, but only 40 were IEMOCAP fear annotations mapped to anxiety. This experiment documents secondary analysis; it does not justify an anxiety-recognition feature. The [text experiment report](../iemocap-text-results.md#affectlab-aligned-six-class-task) also retains the class-difference bootstrap intervals.

### Exploratory six-class contextual-text comparison.

| Metric | Utterance only | Three-turn context | Difference | 95% interval |
| --- | --- | --- | --- | --- |
| Accuracy | 0.5674 | 0.6228 | +0.0554 | [0.0382, 0.0734] |
| Macro F1 | 0.5490 | 0.6222 | +0.0732 | [0.0485, 0.1009] |
| Weighted F1 | 0.5675 | 0.6205 | +0.0529 | [0.0359, 0.0702] |

### Fold variation for the exploratory six-class comparison.

| Fold | Test n | Anxiety n | Utterance only | Context | Difference |
| --- | --- | --- | --- | --- | --- |
| 1 | 1,377 | 12 | 0.5690 | 0.6180 | +0.0490 |
| 2 | 1,357 | 9 | 0.5683 | 0.6655 | +0.0972 |
| 3 | 1,535 | 2 | 0.4992 | 0.5813 | +0.0820 |
| 4 | 1,519 | 7 | 0.5792 | 0.6268 | +0.0475 |
| 5 | 1,632 | 10 | 0.5122 | 0.5870 | +0.0748 |
| Mean ± SD | – | – | 0.5456 ± 0.0330 | 0.6157 ± 0.0304 | +0.0701 |

### Per-class results for the exploratory six-class task.

| Configuration | Class | Precision | Recall | F1 | Support |
| --- | --- | --- | --- | --- | --- |
| Utterance only | Anger | 0.5857 | 0.5576 | 0.5713 | 1,103 |
| Utterance only | Anxiety | 0.3889 | 0.5250 | 0.4468 | 40 |
| Utterance only | Frustration | 0.5420 | 0.5165 | 0.5289 | 1,849 |
| Utterance only | Joy | 0.7073 | 0.6779 | 0.6923 | 1,636 |
| Utterance only | Neutral | 0.5102 | 0.4813 | 0.4953 | 1,708 |
| Utterance only | Sadness | 0.5004 | 0.6347 | 0.5596 | 1,084 |
| Three-turn context | Anger | 0.6089 | 0.5476 | 0.5766 | 1,103 |
| Three-turn context | Anxiety | 0.5778 | 0.6500 | 0.6118 | 40 |
| Three-turn context | Frustration | 0.5579 | 0.5809 | 0.5692 | 1,849 |
| Three-turn context | Joy | 0.7996 | 0.8026 | 0.8011 | 1,636 |
| Three-turn context | Neutral | 0.5174 | 0.4690 | 0.4920 | 1,708 |
| Three-turn context | Sadness | 0.6333 | 0.7408 | 0.6828 | 1,084 |

Context improved frustration, joy, and sadness with intervals above zero. Anger and neutral intervals spanned zero. Although anxiety F1 increased by 0.1650, the interval was wide and the result arose from only 40 examples. It cannot support a strong class-specific or deployment claim.

## Operational packaging diagnostic

The single chain packaged for full-data models selected text/audio weights of 0.59/0.41 and temperature 0.5989. On pooled test-role predictions it produced accuracy 0.7736, macro F1 0.7776, weighted F1 0.7728, ECE 0.0242, NLL 0.6075, and Brier score 0.3280. Across rotating folds, however, each utterance label participated in a validation role before the same label was used with a prediction from a different test-role model. The values describe the packaged transformation but are not an independent held-out performance estimate.

The [multimodal experiment report](../iemocap-multimodal-results.md#final-global-calibration-chain) records the full calibration chain and additional intermediate diagnostics. The [canonical packaging analysis](results-and-provenance.md#operational-packaging-analysis-not-independent-held-out-performance) retains the compact diagnostic table separately from held-out results.
