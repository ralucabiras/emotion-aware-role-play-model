# Interactive conversation replay

Implemented 27 September 2026. Open a completed or interrupted rehearsal from saved sessions, then select **Replay**.

The timeline selects a saved user/assistant exchange. The transcript highlights the selected pair; evidence buttons focus and highlight the original utterance. Highlighting covers the whole utterance because exact spans were not recorded. Native buttons, visible focus and a single-column mobile layout support keyboard and small-screen use.

Three separate panels show observable language features, controller actions/stage transitions/response strategy, and estimated affect with pacing. The labels describe recorded rules and estimates, not personal competence, private model reasoning or measured psychological benefit. Feedback has its own evidence links, resolved through the stored evidence number and conversation-turn UUID. Decision evidence can include earlier turns and is labelled accordingly.

Technical details expose saved before/after states, reason codes, generation source, versions, inference timings, modality availability, per-modality distributions and fused confidence. Missing voice predictions remain gaps. Low confidence, disagreement and inference fallback are explicit. No audio is loaded or retained by replay.

## Data and boundaries

`ConversationReplay.tsx` uses `rehearsalReplay` to project the existing owner-checked session GET response. No new endpoint, database field, generation call, analysis call or scoring pass is needed. The saved decisions are not changed. Rewind already removes discarded turns and decisions; the projection also rejects decisions whose linked turns are absent from the visible transcript.

The transcript runs from `started_at` through `measurement_ended_at`. Older sessions use `completed_at`, including the closing assistant reply paired with a pre-completion user message, consistent with the backend's legacy measurement boundary. Timestamp comparisons preserve the backend's microsecond precision. Later reflection is excluded. Reflection while an attempt was paused remains in the chronological transcript, but has no controller decision and is not presented as a scored exchange.

Legacy sessions show available transcript and language evidence with “Decision details unavailable”. Unlinked legacy evidence is displayed without guessing its source. A record with no completion boundary cannot safely distinguish rehearsal from later reflection, so replay explains the limitation and points to Reflect for the full conversation. Empty records and unavailable feedback have explicit states.

The existing `InsightPanel` expects transient cognitive assessments that are not persisted; replay deliberately uses a separate component rather than reconstructing those assessments. Data retention, ownership and deletion remain those of the original session.

Leaving Feedback for Replay retains the existing questionnaire-close behavior and refreshes the session version. That navigation can write the questionnaire closure; inspecting replay itself performs no writes. Returning to Feedback does not reopen ratings. The frozen study controller and measurement rules are unchanged.

## Synthetic demonstration

1. Start additional workload practice with a character profile. Describe an overloaded workload and ask to prioritise specific work.
2. Respond to the manager's recorded delivery constraint with a supported trade-off; explicitly confirm the resulting proposal. Finish the rehearsal.
3. Open Replay, select the objection exchange, and inspect its saved action, stage transition and recorded objection.
4. Use **View evidence** to jump to the actual request. Select the final exchange and inspect the saved outcome/agreement in technical details.
5. Use **View feedback evidence** to inspect the source of a feedback metric, then reload the session and repeat the link navigation.
6. For uncertainty and failure demonstrations use the explicitly synthetic fixtures in `frontend/e2e/replay.spec.ts`. They cover conflicting model outputs and inference failure without claiming live-model accuracy.

## Verification and limits

Browser fixtures cover desktop/mobile replay, keyboard evidence navigation after reload, accessibility, recorded versions, legacy records, missing boundaries, empty transcripts, disagreement, low confidence, failure and interrupted attempts. Projection checks cover discarded decisions, later reflection, legacy closing replies, microsecond cutoffs and input immutability. Existing backend tests cover actual MongoDB reload, persisted decisions/predictions, rewind and measurement boundaries.

Browser tests use API fixtures; this step does not claim a full-stack browser/backend restart demonstration or evaluate model accuracy. Branching and comparison remain Step 5.
