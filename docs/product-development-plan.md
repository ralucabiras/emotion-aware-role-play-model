# AffectLab product development plan

Status: Steps 1-6 implemented, 28 September 2026. Step 6 is ready for interaction review; Step 7 remains planned. The frozen study protocol is unchanged.

## Objective

Develop AffectLab into an explainable, adaptive conversation simulator for preparing for difficult everyday conversations. The central demonstration should be: prepare a situation, rehearse, handle pushback, inspect the interaction, try another approach, and leave with a practical plan.

Prioritise depth and coherence over feature count. The main technical contributions are dialogue control, integration of trained multimodal models, uncertainty-aware adaptation, reproducible decision explanations, and branching practice. Existing research administration remains available but does not drive the product experience.

## Recommended sequence and stopping points

| Step | Deliverable | Relative scope | Dependency |
| --- | --- | --- | --- |
| 1 | Stateful workload rehearsal and reusable dialogue engine | Large | Existing application |
| 2 | Boundary, relationship, and character behaviour | Medium | Step 1 |
| 3 | Multimodal-informed interaction with user control | Large | Step 1 decision records |
| 4 | Interactive conversation replay | Medium | Steps 1 and 3 |
| 5 | Branch and compare | Large | Stable snapshots and replay |
| 6 | Personal conversation preparation and action card | Medium | Stable scenario engine |
| 7 | Integrated demonstration and engineering evaluation | Medium | Selected preceding features |

Steps 1-4 form the recommended core upgrade. Step 5 is the strongest additional demonstration feature. Step 6 increases everyday applicability and can be postponed if time becomes constrained. Step 7 is required for whichever scope is completed. Scope labels are comparative, not calendar estimates; estimate each implementation after its design slice is agreed.

Each step should be independently demonstrable, tested, and reviewed before starting the next. Add the data needed by the next feature when it is naturally produced, but do not build all screens at once.

## Shared implementation rules

- New behaviour is versioned. Store scenario, dialogue-policy and scoring versions with each attempt. Preserve the original meaning of existing records; old feedback is not silently recalculated.
- Introduce enhanced rehearsals through ordinary additional practice first. Keep frozen required study tasks on their existing behaviour until a deliberate protocol revision. Do not rewrite the frozen protocol as part of UI work.
- Completion, user finish, turn limit and interruption remain distinct. Later reflection must not change completed measurements. Branches and retries do not replace required attempts.
- Preserve the current text-only route and deterministic offline generator. Missing models or provider failures must leave a usable rehearsal.
- Decision explanations describe stored application decisions, not private model reasoning or post-hoc claims invented by a language model.
- Reuse account ownership checks, session concurrency handling, retention and deletion. Do not create a separate permissions system for these features.
- Raw recorded audio remains transient. Persist only necessary prediction summaries and provenance under the session's retention policy, with the disclosure updated accordingly.
- Keep synthetic test cases identifiable. Demonstration output is not participant evidence.

## Step 1 - A real multi-stage workload rehearsal

### Implementation status - 26 September 2026

Implemented for new additional-practice workload attempts at intermediate difficulty. See [the versioned policy, limitations and synthetic demo](workload-dialogue-v2.md).

- Explicit explain -> constraints -> agreement -> resolved stages, with a disclosed Friday client-report constraint and bounded supported trade-offs.
- Persisted versioned decisions, evidence links and snapshots; deterministic feedback separates observable features from completion.
- Progress labels in the workspace; pause/resume, exact snapshot rewind, early finish, turn-cap and safety interruption handling.
- Legacy sessions, required study tasks and study retries retain the original policy. Feedback comparisons require the same scoring version.
- Offline wording and validated online fallback share the same authoritative controller. Free online paraphrasing is intentionally deferred until it can be validated.

Validation: the full backend suite passed with real MongoDB enabled (159 tests); desktop/mobile progress and pause/reload accessibility checks passed (2 tests); frontend production build and lint passed. This includes the additional paraphrase and negation fixtures. Real MongoDB checks recreate repository and service instances; a full-stack browser/backend-process restart demonstration remains part of Step 7. Step 2 now extends this initial slice while preserving stored workload-v2 attempts. Interactive replay and branching remain future steps.

### Purpose and experience

Replace immediate keyword-based success with a conversation that has a clear beginning, objection, negotiation and resolution. A user should have to respond to another person's position, not merely produce a sentence containing a request and a deadline.

Example: the user describes excessive workload; the manager asks which work is at risk; the manager raises a delivery constraint; the user proposes a trade-off; both reach a specific agreement.

### First implementation slice

Implement workload only, using the existing manager scenario and intermediate difficulty. Add a small progress indicator using participant-friendly labels: explain the situation, discuss constraints, agree a plan. Keep detailed policy information in replay rather than filling the chat with developer terminology.

### Technical design

Introduce explicit dialogue stages, allowed transitions and scenario-specific completion requirements. Track the character's current objection, which constraints have been addressed, proposed options and the final agreement. Keep the controller authoritative: generation phrases the selected action but cannot decide that a task is complete.

Expand evidence extraction with bounded features for problem description, request, supporting detail, acknowledgement of an objection, trade-off and agreement. Document that these are observable language features, not a measure of personal competence. Cover paraphrases and negations; keyword presence alone must not establish agreement. Start with auditable rules and examples. Consider structured semantic extraction only if the tests show a concrete need, with validation and an explicit unavailable/uncertain result.

At each exchange save a compact decision record: linked user/assistant turn IDs, state before and after, chosen action, transition reason codes, evidence references, policy/scoring versions and generation source. Save coherent snapshots so rewind restores the actual prior state rather than attempting to reconstruct it from turn counts.

Keep success separate from feedback scores. Reaching a turn cap ends an attempt without claiming that an agreement occurred. A user can still pause or finish early. Do not force unnecessary turns when the relevant interaction requirements have genuinely been met.

Likely files: roleplay_service.py, conversation_service.py, domain.py, chat.py and RolePlayWorkspace.tsx.

### Acceptance checks

- One opening request does not immediately complete the enhanced workload task.
- Relevant responses advance the stages; unrelated messages do not.
- A rehearsed objection and an explicit workable agreement can produce success.
- Pause/resume, rewind, early finish and interruption leave coherent state and evidence.
- Offline and online wording follow the same permitted transitions.
- MongoDB reload and backend restart preserve the stage, decisions and evidence.
- Legacy sessions and frozen required tasks retain their original behaviour.

### Demonstration deliverable

A manager conversation that takes several meaningful exchanges and ends with an identifiable agreement supported by the transcript.

## Step 2 - Scenario-specific behaviour and believable characters

### Implementation status - 26 September 2026

Implemented. See [scenario dialogue v3: policy tables, limits and demonstration](scenario-dialogue-v3.md).

- Added separate boundary and relationship stage policies, versioned definitions, allowed transitions/actions and scenario-specific feedback.
- Added cooperative, rushed and sceptical profiles with visible setup descriptions and persisted selections. Difficult level changes evidence/pressure requirements independently of affect confidence.
- Boundary completion requires refusal through renewed pressure and respectful closure, with no concession or character agreement required.
- Relationship practice can reach a compatible next step or an explicitly unresolved disagreement; polite wording alone cannot obtain acceptance.
- Extended workload with profile-specific constraints; retained the original workload-v2 policy for saved sessions and requests without a profile.
- Reused Step 1 decisions, evidence, snapshots, rewind, ownership and persistence. Required tasks and study-associated retries remain on the frozen controller. Custom and other scenarios remain usable, with generic custom-flow limitations shown in setup.
- The standard browser practice flow selects a profile; older API clients opt in using `character_profile`. Freely paraphrased online dialogue remains deferred under the existing authoritative-wording guard.

Validation: 200 backend tests passed with real MongoDB enabled; after tightening the delivery-check rule, all 58 focused scenario/workload tests passed. Desktop/mobile profile selection, persisted pressure and outcome wording checks passed (8 checks); the broader practice/study browser regression exercised 40 cases, with the two boundary-wording failures corrected and verified by the focused rerun. Frontend build/lint, backend Ruff and diff checks passed. The browser tests use API fixtures; real MongoDB recovery is tested at the repository/service boundary. No Step 3 multimodal adaptation or Step 4 replay screen is included in this step.

### Purpose and experience

Apply the engine to boundary and relationship conversations without making them copies of workload negotiation. Add a small set of character behaviour profiles that visibly change the interaction.

Boundary: clear refusal, response to renewed pressure, respectful closure. A successful boundary does not require the character to agree or the user to offer a concession.

Relationship: describe a situation and need, hear the other perspective, clarify a practical request, and reach a next step or a clearly recorded unresolved ending. A character's agreement must not be guaranteed by choosing polite words.

### Technical design

Represent each scenario as a versioned definition of stages, evidence requirements and available character actions. Start with cooperative, rushed and sceptical profiles. Map profiles and difficulty to concrete differences such as objection type, follow-up specificity and permitted pressure. Bound adaptation so characters remain consistent; do not randomly change their personality each turn.

Provide a visible description before starting, such as 'Your manager is short on time and will ask you to prioritise.' Make user-selected challenge level independent of model confidence. Preserve the familiar difficulty choices.

Custom scenarios initially use a documented generic flow with limited supported skills. Do not imply they receive scenario-specific logic that has not been implemented. Later preparation can compose from these supported flows.

### Acceptance checks

- The same opening can lead to meaningfully different, profile-appropriate objections.
- Each core scenario has its own success requirements and unresolved outcomes.
- Harder difficulty affects interaction behaviour, not merely wording length.
- A boundary can succeed without compromise; a relationship disagreement is not automatically failure.
- Custom scenarios and existing scenarios outside the three core tasks remain usable.

### Demonstration deliverable

Show the same situation with two character profiles and explain the controlled difference in behaviour.

## Step 3 - Connect multimodal predictions to interaction

### Implementation status - 27 September 2026

Implemented. See [exchange-linked multimodal pacing v1](affect-pacing-v1.md) for the policy table, API contract, privacy behavior, limitations and synthetic demonstration.

- Unified optional audio, final reviewed text, server-owned inference and response selection into one versioned chat submission. Stale/duplicate writes are rejected; clients cannot supply authoritative predictions.
- Added explicit keep-going, gentler-pace and more-challenge choices, plus opt-in automatic acknowledgement/pacing offers. The policy preserves benchmark labels and keeps them separate from lexical arousal, anxiety, resistance and intent.
- Stored linked per-modality/fused prediction summaries, uncertainty/disagreement, provenance, actual timings, preference, action and fallback reasons. Raw audio remains transient.
- Added a stored exchange explanation in the workspace, updated the audio/summary disclosure, and preserved independent transcription, text-only use, offline fallback and frozen required-task behavior.
- Reused existing session ownership, optimistic writes, retention, deletion, decisions and rewind. The memory repository now applies version checks to the new submission path as well.
- Pacing changes acknowledgement/prompts only; scenario difficulty, profile and completion rules stay fixed. Automatic adaptation is off by default. Interactive replay remains Step 4.

Validation: 229 backend tests passed with real MongoDB enabled. After synchronizing version tokens for rename and feedback navigation, the focused API/policy checks and desktop/mobile feedback, voice and explanation checks passed. Twelve distinct desktop/mobile cases covered transcription without models, edited voice submission, draft recovery, saved explanations and feedback/rating navigation. Frontend build and lint, backend Ruff and diff checks passed. Tests use synthetic model outputs to evaluate application behavior, not live model accuracy or psychological benefit.

### Purpose and experience

Make the trained text/audio models contribute to the conversation rather than appearing only in a separate result panel. Keep the contribution modest, explicit and under user control.

A user records a reply, reviews its transcription, and sends it. The server analyses the submitted words and recording together. When evidence is uncertain or conflicting, the app keeps the challenge unchanged or offers a neutral pacing choice. The user can request 'keep going', 'gentler pace' or 'more challenge' without accepting an inferred emotion label.

### Technical design

Unify message processing so analysis and response selection use the same submitted message and session version. Prefer one orchestrated submission with optional audio. If a two-step flow remains necessary, use a short-lived server-owned analysis reference bound to message, session and version; never trust client-supplied emotion scores as authoritative.

Keep benchmark emotion labels distinct from arousal, anxiety, resistance and user intent. Define a small versioned policy table describing which measured signals may affect which actions. An emotion label alone must not trigger a claim about a psychological construct the model did not measure. Initial adaptation can favour acknowledgement or offer pacing controls; stronger automatic difficulty adaptation should require an explicit, defensible signal or user preference.

Record modality availability, per-modality and fused estimates, confidence, disagreement, user preference, resulting action and fallback reason. Handle unsupported categories without forcing them into the lexical label set. Low confidence should reduce reliance on the estimate, not itself be interpreted as user distress. Any smoothing or hysteresis belongs in a separately documented policy with tests.

Transcription stays independent of multimodal availability. Editing the transcript invalidates any estimate based on the previous words. Inference failure falls back to text behaviour with a clear status; raw audio is not persisted or embedded in replay.

### Acceptance checks

- A prediction is linked to exactly the exchange it influenced.
- Edited text, stale session versions and repeated submissions cannot attach the wrong estimate.
- Policy tests cover agreement, disagreement, low confidence, missing audio and model failure.
- User pacing preferences take precedence over automatic suggestions.
- Disabling affect adaptation yields the documented baseline behaviour.
- Model source and latency are accurate; the UI does not label heuristic output as trained-model output.

### Demonstration deliverable

A voice rehearsal with an inspectable explanation of whether multimodal evidence changed the response. Explain that the policy expresses a design choice, not a proven psychological benefit.

## Step 4 - Interactive conversation replay

### Implementation status - 27 September 2026

Implemented. See [conversation replay: data boundaries, limitations and synthetic demonstration](conversation-replay.md).

- Added a Replay workspace for completed and interrupted rehearsals, using saved sessions and their existing ownership/retention rules.
- Added a selectable turn timeline, highlighted transcript pairs, keyboard-focusable utterance evidence links and linked feedback evidence. No exact spans are invented.
- Separated observable language, controller actions/stages/strategy, and estimated affect/pacing. Expandable technical details expose saved states, reasons, distributions, uncertainty, disagreement, versions and generation/inference provenance.
- Excluded later reflection using the recorded measurement boundary, preserved legacy closing replies and microsecond precision, and ignored decisions with discarded/missing turns.
- Added honest legacy, missing-source, prediction failure, empty transcript and unknown-boundary states. Replay does not regenerate responses, predictions or feedback.
- Kept existing questionnaire closure on leaving Feedback, refreshing the session version before replay opens. Inspecting replay itself is read-only; frozen study behavior is unchanged.

Validation: 56 focused backend tests passed with real MongoDB enabled, covering saved decisions/predictions, reload, rewind and completion measurement boundaries. All 48 desktop/mobile replay and practice regression checks passed, including evidence navigation after reload, keyboard/accessibility, missing/failing predictions and questionnaire navigation. Frontend build/lint and diff checks passed. Browser fixtures are synthetic; this step does not claim live-model accuracy or a full-stack browser/backend restart demonstration.

### Purpose and experience

Turn a completed rehearsal into something users can inspect and learn from. Show a transcript beside a turn timeline. Selecting a turn highlights the evidence, dialogue stage, strategy, model confidence and any adaptation at that moment.

### Technical design

Build replay from the immutable per-exchange decisions introduced earlier. Add evidence links that navigate to the actual utterance; show exact highlighted spans only when spans were recorded reliably. Reuse the existing InsightPanel where suitable.

Separate estimated affect, observable communication features and controller actions visually. Missing voice estimates should remain gaps rather than invented values. Show uncertainty, disagreement and model/policy versions in expandable details. Prefer clearly labelled distributions or small timelines over a single misleading 'emotional improvement' score.

Provide two levels of detail: a plain-language review for normal use and an expandable technical view for the dissertation demonstration. Existing sessions without decision records show the transcript and available evidence with an honest 'decision details unavailable' state.

### Acceptance checks

- Clicking evidence opens the correct turn after reload.
- Replay matches recorded decisions and never regenerates past explanations.
- Later reflection and discarded rewind history do not appear as part of completed rehearsal measurements.
- Missing predictions, legacy records and failures have clear empty states.
- Keyboard and mobile users can navigate the timeline and details.

### Demonstration deliverable

Walk through an objection, explain the selected action, and show the evidence for both progression and feedback.

## Step 5 - Branch and compare

### Implementation status - 28 September 2026

Implemented. See [branch and compare: contract, boundaries and synthetic demonstration](branch-and-compare.md).

- Added ?Try a different response here? to supported replay turns and a separate saved retry restored from the exact pre-turn snapshot. Source sessions, evidence, ratings and takeaways are preserved.
- Persisted parent/version, branch point, group, copied-context IDs, pre-turn state and deterministic generation mode. Scenario, profile, difficulty and supported policy versions remain fixed.
- Added a two-continuation Compare view showing shared context once, actual responses, observable language, stages/actions, generation provenance and outcomes/agreements. Keyboard, mobile, loading, recovery and unavailable-parent states are covered.
- Added owner-checked branch/comparison endpoints, version validation and idempotent request handling across concurrent requests/restart. Unsupported legacy, frozen required-task and shared-context branch points offer a fresh attempt. Rewind cannot remove inherited context.
- Parent deletion leaves the child usable; account deletion removes all owned branches. Changed originals are not silently substituted in comparison.
- Feedback for branches uses new response evidence only; copied messages/events are not counted as new research activity. Export v4 labels branch context and feedback scope while preserving historical frozen snapshots and required-attempt selection.

Validation: the full backend suite passed with real MongoDB enabled (243 tests); all 14 final branching tests passed after adding the boundary/relationship demonstrations. All 66 desktop/mobile branching, replay, practice and workspace-recovery checks passed; the six focused branch cases passed again after the final retry-recovery adjustment. Frontend build/lint, backend Ruff and diff checks passed. Browser fixtures are synthetic; MongoDB tests reopen repository/service instances. No live-model accuracy or full-stack browser/backend-process restart claim is made.

### Purpose and experience

Let a user choose 'Try a different response here' from replay. Preserve the original conversation and create an alternative continuation from just before the selected user turn. Compare what changed in language, character responses, stages and agreement.

### Technical design

Create a new session with parent session ID, branch point turn ID, branch group ID and a saved pre-turn state. Copy the context needed to resume, with explicit provenance and stable links. Do not copy post-ratings, completion timestamps, final feedback or takeaways into the new branch. Preserve shared evidence as context while distinguishing it from newly generated branch activity.

Keep branch lineage orthogonal to existing attempt purpose: branches are retries/additional practice and never silently become a required attempt. Freeze scenario, profile and policy versions for a comparable branch; reject unsupported legacy branch points with a clear option to start a fresh attempt.

Show shared context once and alternatives side by side. Compare observable differences, not predictions that one wording will work in real life. If online generation varies, disclose that the comparison also contains generation variability. Deterministic response mode provides a reproducible demonstration.

Start with at most two visible alternatives. Define deletion behaviour so removing a parent leaves a usable child's copied context without dangling UI links, while account deletion removes all owned branches. Research activity counts must not count copied turns as new activity.

### Acceptance checks

- Branching never mutates the original attempt or its ratings.
- The alternative starts from the exact state before the chosen response.
- Copied context is distinguished from new activity in metrics and exports.
- Completion, comparison and evidence refer to the correct branch.
- Parent deletion, reload, concurrency and unsupported branch points behave predictably.

### Demonstration deliverable

Compare an apologetic response with a clear boundary from the same conversational moment, without claiming a guaranteed real-world outcome.

## Step 6 - Personal conversation preparation and action card

### Implementation status - 28 September 2026

Implemented. See [personal preparation and action cards](conversation-preparation.md) for behavior, APIs, limitations and a synthetic household-conversation demonstration.

- Added four-input preparation with an editable brief: role, situation, objective, opening, possible objection, practice focus and supported generic flow. Users explicitly confirm before saving or starting; offline templates and failure recovery preserve entered text.
- Reused custom-scenario validation/storage and added owner-checked editing, including older custom records. Rehearsals retain independent scenario snapshots so later edits cannot rewrite history.
- Added a versioned prepared generic flow with a reviewed objection before completion, deterministic wording and visible limits. Existing unprepared custom scenarios and frozen required study tasks retain their behavior; arbitrary scenario-specific simulation and online brief generation are not claimed.
- Added editable opening/request/fallback/reminder cards, saved separately from scores with ownership and session-version checks. Copy and plain-text download work on current edits. Suggestions are labelled drafts and do not infer external commitments from assistant responses.
- Excluded later reflection, inherited branch wording and crisis utterances from suggested excerpts. Rewind clears a stale card; branches start without one. Existing retention, deletion and research-export privacy boundaries are preserved.

Validation: 252 backend tests passed with real MongoDB enabled; all six focused preparation/card tests passed after adding the missing-boundary case. All 56 desktop/mobile preparation, practice and study-flow checks passed, including keyboard/accessibility, legacy editing, offline/save recovery, reload, copy and download. Frontend build/lint, backend Ruff and diff checks passed. Browser tests use synthetic API fixtures; MongoDB tests reopen repository instances. Live-model accuracy, online brief generation and a full-stack browser/backend-process restart demonstration are outside this step.

### Purpose and experience

Make everyday applicability explicit: 'I need to talk to my manager tomorrow' becomes a practical, editable rehearsal rather than requiring the user to complete a technical scenario builder.

### Technical design

Collect four short inputs: who the person is, what happened, desired outcome and the difficult part. Produce a reviewable brief containing role, situation, opening line, likely objection, target skills and proposed flow. Reuse the existing custom-scenario storage and validation. Generation suggests the brief; the user edits and confirms it before rehearsal begins.

Support the scenario structures already implemented rather than promising arbitrary simulation. Provide a simple template-based brief when online generation is unavailable. Let the user use generic descriptions instead of names or unnecessary personal details.

After practice, offer an editable action card: opening sentence, main request, boundary or fallback, and one reminder. Base it on the conversation and the user's choices. Save it separately from scoring and label generated suggestions. Begin with copy/download text; a printable layout can follow if useful.

### Acceptance checks

- A user can prepare and start a relevant rehearsal without understanding internal skill names.
- The brief can be edited before any rehearsal starts.
- Generation failure preserves entered information and offers a template path.
- The action card contains no invented commitments presented as agreed facts.
- Existing custom scenarios still load and remain editable.

### Demonstration deliverable

Turn an ordinary work or household problem into a rehearsal and leave with a useful plan for the actual conversation.

## Step 7 - Finish the experience and demonstrate the engineering

### Purpose

Present the completed features as one coherent application and verify the claims made about them. This is a technical evaluation package, not a requirement to recruit a large cohort.

### Work

Create a short guided demo using explicitly synthetic scenarios. Show normal text use, a multimodal case, an uncertain prediction, offline fallback, replay and a branch. Make loading, error and empty states consistent. Keep administrative study controls outside the main practice journey.

Extend the browser smoke journey for enhanced practice, persistence, replay and branching as those features land. Exercise real MongoDB, including a backend restart. Retain focused tests for frozen required-task behaviour.

Measure what the system actually does: dialogue transition correctness, false positive/negative evidence cases, model results already supported by held-out evaluation, agreement/disagreement handling, response latency, fallback success and recovery. Compare a fixed dialogue policy with the new policy on the same authored cases; label these engineering fixtures, not participant outcomes. Use repeated online runs only where generation variability matters.

Prepare architecture and sequence diagrams, policy tables, representative replay screenshots, versioned evaluation outputs and a limitations section. Keep claims about usability or communication improvement proportional to any actual user evidence. Confirm the final dissertation framing with the supervisor/course requirements.

### Acceptance checks

- The main demonstration runs from a clean environment with documented configuration.
- Text-only and offline paths work end to end.
- All claimed model/policy contributions can be traced to implementation and evidence.
- No UI reports fabricated scores, hidden filled-in ratings or guaranteed emotional understanding.
- The application and documentation distinguish implemented behaviour from proposed future work.

## Next task to implement

Steps 1-6 are implemented. Review the personal preparation and action-card demonstration in [conversation-preparation.md](conversation-preparation.md). The next implementation is Step 7: finish the integrated experience and produce the engineering demonstration and evaluation package. Frozen required study tasks remain unchanged.
