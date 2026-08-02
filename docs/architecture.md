# Architecture

## Request pipeline

```text
User message
  -> safety phrase check
  -> EmotionAnalyzer
  -> multi-turn state smoothing
  -> cognitive assessment
  -> StrategySelector
  -> role-play policy or ResponseGenerator
  -> assistant turn
```

The backend keeps domain objects in `app/models/domain.py`. Abstract boundaries in `app/services/interfaces.py` separate orchestration from implementations. The current rule-based implementations are transparent baselines, not trained affect models.

## API surface

- `POST /api/sessions` creates an ephemeral session.
- `GET /api/sessions/{id}` returns history and current state.
- `DELETE /api/sessions/{id}` removes the session.
- `POST /api/chat` runs the pipeline.
- `GET /api/roleplay/scenarios` lists scenarios.
- `POST /api/sessions/{id}/roleplay` starts a role-play.

## Recommended next milestones

1. Introduce a repository interface and PostgreSQL persistence with explicit retention controls.
2. Add the other two MVP scenarios and structured post-session feedback.
3. Replace the text analyser with a calibrated pretrained baseline and evaluate it.
4. Add an API-backed LLM implementation with structured prompting, output validation, and moderation.
5. Add experiment configuration and compare generic versus strategy-controlled responses.
6. Only after the text architecture is stable, add opt-in audio and webcam pipelines without raw-media storage by default.

