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

## Deferred work

Trained emotion/cognitive models, experiment tracking, audio, video, password reset, email verification, OAuth, and production deployment hardening remain outside this milestone.

