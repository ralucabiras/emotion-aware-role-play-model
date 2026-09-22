# AffectLab system card

## Intended use

A dissertation research prototype for adults to reflect on and rehearse difficult interpersonal conversations. It supports English-speaking participants aged 18 or older located in Romania. The research question concerns feasibility, usability, and communication practice—not therapeutic effectiveness.

## Inappropriate use

Do not use AffectLab for diagnosis, treatment, clinical triage, emergency response, employment or educational decisions, surveillance, deception, assessment of another person, use by minors, or inference of protected or stable personal traits. Do not claim the affect estimate reveals how someone truly feels.

## Safety and human control

Deterministic crisis-language checks run before generation; optional provider moderation is secondary. A positive check interrupts ordinary coaching. Users can pause, edit transcripts, finish role-play, delete sessions, withdraw from research, or delete their account. The service is not monitored, does not know location, cannot contact emergency services, and may miss indirect or multilingual crisis language.

## Privacy and security

Authentication uses Argon2 passwords, short access JWTs, rotated hashed refresh tokens, ownership checks, and verified email. Remote mode requires HTTPS, explicit hosts/origins, secure cookies, rate limits, and a strong secret. Raw audio is not persisted. OpenAI processing is disclosed and can be disabled. Conversation sessions expire separately from minimized pseudonymous study records.

## Principal limitations

Generated responses may be repetitive, overly agreeable, culturally inappropriate, or wrong. Rule-based feedback detects only observable lexical features. Affect models inherit IEMOCAP limitations described in the model card. The English lexical crisis layer is not a complete safety system. The application is research software, not a clinically validated intervention.
