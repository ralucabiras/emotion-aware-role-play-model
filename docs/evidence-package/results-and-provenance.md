# Canonical results and provenance

Use this held-out-performance table for the dissertation presentation. Do not substitute training-sample smoke-test accuracy or the label-reused global packaging analysis reported separately below.

| System | Accuracy | Macro F1 | Weighted F1 | ECE | Evaluation provenance |
| --- | ---: | ---: | ---: | ---: | --- |
| Utterance-only text | 0.6624 | 0.6651 | 0.6640 | — | Five session-held-out IEMOCAP folds |
| Three-turn context text | 0.7304 | 0.7332 | 0.7300 | 0.0311 | Same folds; validation temperature scaling |
| Audio only | 0.6279 | 0.6349 | 0.6229 | 0.0468 | Same folds; validation temperature scaling |
| Equal-weight late fusion | 0.7832 | 0.7883 | 0.7815 | 0.1619 | Predeclared paired comparison; classification headline |
| Validation-fitted fold fusion | 0.7717 | 0.7758 | 0.7707 | 0.0283 | Fold validation-selected weights and temperature |

Context improved macro F1 over utterance-only text by 0.0681, with dialogue-bootstrap 95% interval [0.0504, 0.0857]. Equal fusion improved macro F1 over paired context text by 0.0551, interval [0.0407, 0.0713]. The equal fusion is the confirmatory classification result, and fold-specific validation-fitted fusion provides the held-out calibration result.

## Operational packaging analysis (not independent held-out performance)

| Configuration | Accuracy | Macro F1 | Weighted F1 | ECE | Provenance limitation |
| --- | ---: | ---: | ---: | ---: | --- |
| Final global calibration chain, applied to pooled test-role predictions | 0.7736 | 0.7776 | 0.7728 | 0.0242 | All 5,531 utterance identities and labels were already used to fit the global chain through their validation-role predictions from other folds |

Different trained models produced the validation-role and test-role predictions, but that does not remove the label reuse. This row describes the single chain selected for full-data packaging and must not be combined with the held-out performance table or cited as additional confirmatory evidence.

## Application performance regression check

The recorded single-client, in-process HTTP benchmark used the memory repository and deterministic fallbacks. It includes routing, authentication, validation, application services, and response serialisation, while excluding network transit, MongoDB, trained inference, external providers, and concurrent load.

| Operation | Samples | Median (ms) | 95th percentile (ms) |
| --- | ---: | ---: | ---: |
| Liveness | 200 | 1.332 | 1.866 |
| Authenticated scenario catalogue | 200 | 2.942 | 3.922 |
| Session creation | 100 | 2.988 | 3.961 |
| Role-play start | 100 | 3.396 | 4.437 |
| Deterministic conversation turn | 100 | 4.659 | 5.836 |

Run `.\.venv\Scripts\python.exe scripts\evaluate_performance.py` from the repository root to regenerate `docs/evidence-package/generated/performance-v1.json`. The command fails if a measured 95th percentile exceeds its deliberately generous regression budget. These timings are a reproducible local baseline, not a production-capacity or external-provider latency claim.

## Exact artifact provenance

- Private roots and fold-artifact locations are recorded in `docs/iemocap-text-results.md` and `docs/iemocap-multimodal-results.md`.
- Final artifact root: `gs://affectlab-research-raluca-biras/models/iemocap-benchmark4-final-v1/`.
- Configuration SHA-256 at preparation: `d1a29a886293d5ed7398afc3208b4e866ef50d78b03b5792c5c66fb4693e0914`.
- Repository commit at preparation: `0411ee550318e6031b5edccce13db74640e99d74`.
- Training environment recorded by final manifests: Python 3.12.13, PyTorch 2.11.0+cu128, Transformers 5.13.1, Tesla T4.
- Final text artifact: DeBERTa-v3-small, 7 epochs, 5,531 examples.
- Final audio artifact: Wav2Vec2-base, 10 epochs, 5,531 examples; 16 kHz; 20-second cap; 16/5,531 files truncated.

Model-file hashes cannot be truthfully recorded until the private final directories are downloaded beside the application. Run `scripts/capture_model_provenance.py` immediately after download and retain its JSON with the dissertation archive. That manifest is the immutable source for individual file and aggregate model hashes.
