# AffectLab product development plan

Status: proposed implementation sequence, 26 September 2026. This plan does not change the application or the frozen study protocol.

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

## First task to implement

Start with Step 1: enhanced workload rehearsal. The first reviewable milestone is one complete multi-stage manager conversation, with state persisted across reloads, evidence-linked feedback and no regression to existing required study tasks. Approve that interaction before extending it to other scenarios or adding multimodal adaptation.
