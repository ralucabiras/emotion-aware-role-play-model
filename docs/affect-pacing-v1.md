# Exchange-linked multimodal pacing v1

Implemented 27 September 2026 for Step 3. This is an application policy, not evidence that an emotion estimate reveals anxiety, intent, resistance, competence or a psychological benefit.

## Experience and scope

During an active enhanced rehearsal, the user may record speech, review/edit the transcript, choose a pace, and send. The server receives the final words and optional recording in one chat submission. It computes the local trained-model estimates and selects a bounded pacing action for that exact exchange. Transcription remains an independent service and still works when local multimodal models are unavailable.

Automatic voice-informed acknowledgement/pacing suggestions are **off by default**. The user can enable them or explicitly choose **keep going**, **gentler pace** or **more challenge**. An explicit pace takes precedence over automatic suggestions, even when automatic adaptation is disabled or inference is unavailable. Pacing preferences affect wording for the submitted exchange; they do not silently change the scenario difficulty, character profile, success requirements or feedback scores. Controls keep their chosen setting while the workspace remains open; reloading starts with automatic suggestions off again.

Only active enhanced workload/boundary/relationship rehearsals without a required-study association can adapt. Paused/completed rehearsals, ordinary reflection, legacy sessions, required study tasks and study-associated retries use baseline behavior and skip new multimodal inference. Safety interruptions take precedence over inference and pacing. Completed attempts receive their ordinary closing response without an additional pacing question.

## Policy table: affect-pacing-v1

The implementation is `backend/app/services/affect_pacing.py`. Conditions are evaluated in this order:

| Condition | Action | Effect |
| --- | --- | --- |
| Safety, completed exchange, or ineligible session | baseline | No pacing addition |
| User chooses keep going | baseline | No automatic acknowledgement or pacing offer |
| User chooses gentler pace | gentler | Add permission to take time and address one point at a time |
| User chooses more challenge | more_challenge | Add a prompt to be specific about what they can commit to |
| Automatic adaptation disabled | baseline | Original scenario wording |
| Audio/model unavailable or inference fails | baseline | Continue the text rehearsal; record the fallback |
| Any unsupported category | baseline | Preserve the model labels without mapping them into lexical labels |
| Any modality/fused confidence below the model's configured low threshold | offer_pacing | Offer a neutral pacing choice; do not infer distress |
| Text/audio disagree, or fused label differs from their matching label | offer_pacing | Offer the same neutral pacing choice |
| Supported matching estimates of anger or sadness | acknowledge | Add the neutral phrase "I hear you." |
| Supported matching happiness/neutral estimates | baseline | No addition |

Supported labels are the existing IEMOCAP benchmark categories `anger`, `happiness`, `neutral`, `sadness`. The choice to acknowledge two categories is a modest authored policy, not a validated clinical intervention. The system never translates those categories into lexical arousal, anxiety, intent or resistance. The existing lexical state tracker continues separately. This policy has no smoothing or hysteresis.

The scenario controller still selects the permitted dialogue action. Its deterministic or validated online wording is generated first; the policy adds the recorded pacing prefix. Generation metadata describes that original wording, while the separate affect decision describes the deterministic addition. Completion and measurements remain controller-owned.

## One submission, one exchange

`POST /api/chat` accepts the final `message`, optional `audio_wav_base64`, `request_id` (UUID), `expected_version`, `adaptation_enabled`, and `pacing`. Version and request ID are required for audio or pacing/adaptation submissions. Unknown fields are rejected, including client-supplied predictions. Plain legacy text-only API requests remain supported.

Create, start, session-read, action, rewind and chat responses expose the session version. Chat also returns the actual saved user turn, so the browser uses the real transcript ID. The browser no longer calls `/affect/multimodal` before chat; that older read-only analysis endpoint cannot affect the conversation.

The server checks ownership, version and prior request IDs before inference. A session snapshot prevents pending submissions from mutating stored state. Existing MongoDB optimistic concurrency commits the exchange atomically; the memory repository now increments/checks versions too, including rejection after deletion. Concurrent requests may both run inference, but only one matching-version write can succeed. Duplicate submissions return 409 rather than replaying a cached response; IDs remain consumed after rewind. No exactly-once inference claim is made.

Changing a transcript before sending needs no estimate invalidation token: no estimate has yet been computed. The exact submitted words are the model target. Draft edits/new recordings clear the displayed prior estimate. Stale versions or repeated IDs cannot attach an estimate to different text. After a conflict or uncertain network result, the user can reload the saved conversation while keeping the draft, review what was saved, and decide whether to send again.

## Stored explanation and privacy

An `AffectDecision` is saved on the assistant turn and, when present, its dialogue decision. It contains the linked user/assistant UUIDs, request ID, pre-exchange session version, policy version, explicit preference, automatic-adaptation setting, text availability, audio submission/usable-estimate status, model availability, prediction source, model version, per-modality/fused distributions and confidences, agreement, inference/queue/overall analysis timing, selected action, reason and fallback reason.

Model probability summaries are validated for bounded distributions, finite probabilities, normalized mass and consistent labels/confidences. Agreement and confidence-level labels are recomputed from the validated values. Invalid estimates fail closed to the usable text path. Model failures expose a short fallback code rather than exception contents. No prediction is called trained-model output unless the configured model service returned a valid estimate.

Raw base64/WAV data never enters a session or research record. Only the submitted text, necessary prediction summaries and provenance are persisted under the existing session retention/deletion policy. Rewind removes the discarded prediction/decision with its turns; request IDs alone remain consumed. Account/session deletion uses the existing repository paths. Later reflection cannot update a completed rehearsal's dialogue decisions or feedback. The workspace disclosure and study-information API now explain prediction-summary storage.

The workspace shows a stored "Last submitted exchange" explanation, including the applied action, reason, source, availability, timings and model/policy versions. Reload uses the saved record; it does not regenerate explanations. This small inspector is not Step 4's interactive replay screen.

## Synthetic demonstration

1. Start additional enhanced workload, boundary or relationship practice with a character profile.
2. Record a reply, edit its transcript if needed, enable automatic suggestions and send.
3. Expand "Why this response?" and inspect the linked reply, estimates, availability and policy reason. Uncertain/conflicting signals offer a choice; confident supported matching signals may add acknowledgement; absent models show a text fallback.
4. Choose keep going to suppress automatic additions, or explicitly request gentler pace/more challenge. These work with text only too.
5. Reload the saved session and inspect the same recorded explanation. Retry the last turn to remove its prediction and restore the earlier dialogue state.

The automated cases use explicitly synthetic prediction stubs, not participant evidence or claims of model accuracy. Actual voice predictions require the existing local trained-model configuration; no real-label outcome is guaranteed for a spoken sentence.

## Verification and limits

Policy fixtures cover matching/disagreeing labels, low per-modality confidence, unsupported categories, missing audio, malformed audio/estimates, unavailable/failed models, explicit preference precedence and the disabled baseline. Service/API tests cover final-text binding, stale/duplicate/parallel requests, real turn IDs, safety/frozen-study overrides and deletion during pending inference. Real MongoDB tests reload summaries through a fresh repository/service and verify rewind and the absence of raw audio. Desktop/mobile browser fixtures cover edited transcripts, one chat request, draft recovery and persisted explanations.

No live model-accuracy evaluation or live provider call was performed for this implementation. Existing model evaluation results retain their original scope. There is no automatic change to scenario challenge requirements, psychological-state inference from benchmark labels, or claimed communication improvement. Model inference exceptions fall back; the existing model service has no new hard execution deadline in this version.

Verification on 27 September 2026: full backend suite 229 passed with real MongoDB; final focused API/policy regression passed after version-token synchronization; 12 distinct desktop/mobile browser cases passed across the targeted runs; frontend build/lint and backend Ruff passed. No live trained-model or provider evaluation is claimed.
