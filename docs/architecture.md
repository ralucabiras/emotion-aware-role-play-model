# Architecture

## Request flow

```text
Authenticated user
  -> ownership-protected MongoDB session
  -> crisis phrase check + optional moderation
  -> emotion analysis and multi-turn smoothing
  -> cognitive assessment and strategy selection
  -> role-play policy or OpenAI/template response generator
  -> persisted turn and operational generation metadata
```

Interfaces isolate persistence, affect analysis, strategy selection, and generation. Tests use `MemoryRepository`; configured deployments use PyMongo's `AsyncMongoClient`. MongoDB TTL indexes expire inactive sessions after 30 days and expired refresh-token records automatically.

## Security and retention

- Passwords use Argon2 hashes.
- Access JWTs last 15 minutes by default.
- Refresh JWTs are stored only as SHA-256 digests, delivered in an HttpOnly SameSite cookie, rotated once, and revocable.
- Every session lookup includes `user_id`; inaccessible resources return 404.
- Account deletion removes user sessions and refresh tokens.
- JWT secrets and OpenAI credentials come from environment variables only.

## Role-play and feedback

Each scenario defines difficulty behavior, expected skills, success conditions, and a maximum turn count. Per-turn evidence captures observable language features and affect values. Deterministic metrics are the source of truth; the LLM may rephrase strengths and suggestions but cannot create new evidence.

## Text-intelligence baseline

The `lexical-v2` analyzer returns a normalized eight-label distribution plus valence, arousal, intensity, and confidence. It handles weighted terms, nearby negation, intensifiers, and punctuation. `cognitive-rules-v2` independently estimates ten tentative cognitive-pattern categories, user intent, advice readiness, resistance, and a possible stated cause. The state tracker applies an exponential moving average across turns.

The strategy policy scores every available strategy and returns the chosen strategy with human-readable reasons. Crisis escalation has absolute precedence. These transparent components establish evaluation and ablation baselines; they are not trained models and must not be described as clinically validated.

Experiment configuration lives in `configs/text_baseline.json`. The JSONL evaluator under `ml/evaluation` accepts records containing `text`, `emotion`, and optional `distortion`, and can write a reproducible JSON result with `--output`.

## Implemented optional services and remaining scope

Email verification and password reset are implemented through the configured SMTP provider. OpenAI-backed reflection, adaptive role-play, feedback phrasing, moderation, and transcription are available behind deterministic fallbacks. The optional multimodal inference boundary lazy-loads private local text/audio artifacts, constructs the previous-three-turn causal text format from an authenticated user's owned session, validates an in-memory WAV payload, and discards audio after inference. It returns the four-class research distribution separately from the persisted conversational affect state. The trained estimate never overrides crisis detection or safety escalation.

All network-backed features can be disabled for an offline demonstration. OAuth, video inference, multilingual support, trained-model hosting, external experiment tracking, and a production hosting platform remain outside the implemented scope. Remote-pilot deployment controls and limitations are documented separately in `docs/remote-pilot-security.md`.
