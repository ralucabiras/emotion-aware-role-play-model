# Scenario dialogue and character profiles v3

Implemented 26 September 2026 as Step 2 of the product development plan. All examples and tests below are synthetic engineering fixtures, not participant evidence.

## Starting profiled practice

Choose workload, boundary or relationship in ordinary additional practice, select a difficulty and a **cooperative**, **rushed** or **sceptical** character, then begin. The profile description appears before starting and remains visible during the attempt. The profile and challenge level stay fixed independently of affect confidence.

The browser selects cooperative by default for these three scenarios. API clients opt in with `character_profile`; omitting it preserves the previous behavior, including intermediate additional workload v2. Saved attempts are never upgraded. Required study tasks and retries associated with a required task reject profiles and retain the frozen controller. Ordinary retries without a required-task association can use profiles.

Custom scenarios and other existing scenarios retain their established flow. Custom practice asks generic follow-up questions and checks the selected observable language features; it does not claim a specialized boundary, relationship or workload controller. This limitation is visible in setup.

## Versioned definitions

`backend/app/services/scenario_dialogue.py` defines stages, participant-facing labels, feature checks, allowed transitions, available character actions and outcomes. Every transition is checked against its scenario definition. The shared controller handles lifecycle, caps and feedback; scenario policies select the response action. All profiled attempts store policy `scenario-dialogue-v3`, scenario/scoring versions `workload-v3`, `boundary-v3` or `relationship-v3`, and the selected profile. Decisions store the profile and reason codes alongside the existing snapshots and generation provenance.

| Scenario | Stages | Resolution requirements | Other endings |
| --- | --- | --- | --- |
| Workload | Explain, constraints, agreement | Respond to the Friday client-report constraint, propose a supported trade-off, meet profile/challenge requirements and explicitly confirm | User finish, cap without agreement, safety interruption |
| Boundary | Refuse, pressure, respectful closure | Refuse, reaffirm after bounded renewed pressure, close respectfully | User finish, cap without held boundary/closure, safety interruption |
| Relationship | Situation and need, other perspective, next step | State situation and need, acknowledge the other perspective, propose a compatible practical request, confirm | Explicit unresolved disagreement, user finish, cap, safety interruption |

Boundary success is `boundary_held`: it never requires a concession, an alternative favor or the character's agreement. The sceptical friend may remain disappointed. A respectful closure can complete the last pressure exchange without an extra turn. If the user changes their answer during closure, the controller asks them to clarify and reaffirm the boundary.

Relationship success is `next_step`. A user can instead say "Let's agree to disagree" or "Leave this unresolved" after hearing the other perspective. This completes with reason/outcome `unresolved`, no final agreement and no claim of personal failure. Politeness alone cannot override the character's availability or requirement for a trial. Revised requests go back for review rather than inheriting the previous proposal's acceptance.

Completion remains distinct from language-feature scores. Later reflection leaves the rehearsal decisions, feedback and measurement boundary unchanged. Pausing does not advance the scenario; rewind restores the stage, objections, proposal, outcome and pressure count from the actual saved snapshot.

## Concrete profile and difficulty behavior

| Profile | Workload | Boundary | Relationship |
| --- | --- | --- | --- |
| Cooperative | Explores the delivery/trade-off | Asks for reconsideration once at beginner/intermediate | Shares fatigue after work, considers a manageable timed conversation |
| Rushed | Requests concise priorities; proposals over 45 words prompt a shorter reply | Asks for an immediate answer or partial help, without requiring the user to concede | Declines work-night/tonight proposals and requires a weekend request |
| Sceptical | Requires a progress check before accepting a trade-off | Adds one renewed-pressure exchange and can close without agreeing | Requires a small trial and a review before considering a next step |

Difficult level adds one boundary-pressure exchange (maximum three with the sceptical profile). Difficult workload requires a progress check regardless of profile. Difficult relationship requires a trial and review regardless of profile. Beginner/intermediate share the same minimum interaction requirements in this version; the meaningful increase in controller requirements occurs at difficult. Pressure is deterministic and bounded; the character never randomly changes profile. Affect estimates do not select these requirements.

Workload progress checks must name Monday through Thursday, before Friday, or before delivery in the check-in clause; a Saturday check or unrelated weekday mention does not satisfy the delivery constraint. For workload, supported trade-offs remain moving other/admin/internal tasks or a project/presentation to Monday or next week, or handing work to a colleague/teammate. For relationship, practical requests include talking, checking in, spending time, sitting together, walking or having dinner with an explicit time. Rushed relationship requires a weekend reference in the actual request, not elsewhere in the message.

## Evidence and limitations

Rules use bounded phrases and clauses with negation checks. They distinguish a refusal from "I cannot say no" or a reversal such as "I cannot take this on, but I'll do it." Hostile wording does not establish respectful closure. Negated requests and unrelated commitments do not establish a next step. Uncertainty and conditions block confirmation.

This is not general semantic understanding: indirect refusals, sarcasm, unusual paraphrases and complex contradictory clauses may be missed. The authored relationship situation focuses on time together; arbitrary relationship conflicts are not claimed to be supported. The workload situation remains the disclosed Friday report. Character responses and constraints are designed rehearsal behavior, not predictions of real people.

Online generation retains the Step 1 guard: it cannot decide transitions and wording that differs from the authoritative policy text falls back. This version therefore demonstrates consistent authored character behavior; it does not claim unconstrained LLM characters or live-provider validation.

Storage, owner checks, optimistic concurrency, retention and deletion use the existing session repository. There is no new collection or permission system. Raw audio handling is unchanged. Evidence UUIDs refer to the existing transcript, and feedback turn numbers resolve through those stored evidence records. Interactive replay remains Step 4.

## Demonstration: one refusal, two profiles

1. Start intermediate boundary practice with **cooperative**.
2. Say "I cannot take this on." The friend asks for reconsideration.
3. Say "My answer is still no. Thank you for understanding." The boundary resolves without compromise.
4. Start a new intermediate boundary practice with **sceptical** and use the same opening and response. The friend questions the refusal and raises one further objection.
5. Reaffirm the same boundary once more. The friend remains disappointed, but the attempt resolves because the user held the boundary and closed respectfully.

For relationship practice, try:

1. "When we spend evenings apart, I feel lonely and I need time together."
2. "I understand you are tired. Could we talk for 20 minutes on Saturday as a trial and review it on Sunday?"
3. "Agreed."

With the rushed profile, try a tonight-only proposal at step 2 to see it declined. Then use the weekend proposal, or explicitly leave the disagreement unresolved. For workload, compare the same trade-off with cooperative and sceptical profiles; the latter requires a progress check before acceptance.

## Verification

Synthetic tests cover all profile/difficulty combinations for boundary and relationship, distinct objections, workload requirements, irrelevant/negated/reversed replies, capped and unresolved endings, fixed behavior across affect confidence, legacy compatibility and snapshot recovery. API tests cover validation, ownership and persisted profile/outcome data. Real MongoDB tests recreate repository/service clients and continue and rewind both new scenario flows. Browser tests cover profile selection, saved pressure/profiles, honest outcome wording and desktop/mobile accessibility; these use API fixtures, not a claimed full-stack browser study.

Verified locally: the full backend suite passed 200 tests with real MongoDB enabled. The final delivery-check refinement and new regression case passed in the 58-test focused scenario/workload suite. All 8 new desktop/mobile browser checks passed after fixing outcome wording; the broader practice/study regression also exercised existing custom and frozen-study flows. Frontend production build, ESLint, focused backend Ruff and diff checks passed. Live provider generation and a full backend-process/browser restart demonstration were not run.
