# Enhanced workload rehearsal v2

Implemented 26 September 2026. This is an engineering practice feature, not a revision to the frozen study protocol.

## Availability

Start **additional practice**, choose **Workload conversation**, and select **intermediate** difficulty. Only new attempts with this combination use `workload-v2`. Required tasks, study retries, other difficulties/scenarios, custom scenarios and saved legacy attempts retain their existing controller. Scenario, policy and scoring versions are stored on the attempt. Feedback comparisons require matching scoring versions.

## Authoritative policy

| Current stage | Required observable evidence | Next stage / manager action |
| --- | --- | --- |
| Explain the situation | Problem, request and supporting detail (may accumulate across exchanges) | Discuss constraints; raise the client report's Friday deadline |
| Discuss constraints | Acknowledge the deadline, preserve the report for Friday, and propose moving other work to Monday/next week or delegating it to a colleague | Agree a plan; ask for confirmation |
| Agree a plan | Explicit affirmative commitment without negation, uncertainty, a condition or a revised trade-off | Resolved; record the accepted proposal |
| Agree a plan | Revised supported proposal | Stay; ask to confirm the revised proposal |
| Any active stage | Missing or unrelated evidence | Stay; ask the relevant follow-up |
| Any unresolved stage at turn 8 | No confirmed agreement | End with `maximum_turns`, without success |

`user_finished`, `success`, `maximum_turns` and `safety_interruption` remain distinct. Paused reflection does not advance the rehearsal. Later reflection cannot alter completed measurements. A proposal cannot establish agreement in its opening exchange, and a response to the objection must occur after that objection was actually raised.

## Extraction and limits

The auditable rules live in `backend/app/services/workload_dialogue.py`. They identify bounded observable language features, not personal competence or whether a real manager would accept a plan. Feedback checks report feature presence independently of task completion.

Examples include "too many tasks" / "overloaded" / "hours of work"; "could we" / "please" / "help me prioritise"; "understand" / "recognise" / "must"; and "move" / "postpone" / "delegate". Negated clauses are excluded. Negated or conditional confirmations such as "I don't agree", "Yes, but I cannot do that", and "Yes if I get help" cannot finish the task.

This first slice deliberately uses one disclosed client-report constraint and a bounded set of trade-offs. It is not general semantic understanding: indirect language, unusual task names, dates other than the supported examples, sarcasm and complex clause relationships may be missed. Follow-up questions explain the supported trade-offs. No structured semantic extractor is claimed.

## Stored evidence and recovery

Each rehearsal exchange stores user/assistant UUIDs, before/after dialogue and affect snapshots, selected action, reason codes, evidence turn UUIDs, scenario/policy/scoring versions and actual generation metadata. Evidence records contain feature names and their source turn UUID; feedback's turn numbers resolve through those records. No inferred text spans are stored.

Snapshots contain the objection, addressed constraints, proposed options, final agreement, turn, progress, difficulty, cooperation, affect and status. Rewind restores the preceding snapshot, removes the discarded decision/evidence and its research events, and clears completion feedback. Rewind after post-ratings or after unrelated reflection remains prohibited by existing session rules. Safety interruptions preserve prior evidence and record an interruption decision.

State lives inside the existing session document and uses the existing owner checks, optimistic MongoDB concurrency, retention and deletion paths. There is no new database or permissions system.

Online output cannot select transitions. For this first version, enhanced wording is accepted only if it matches the authoritative wording; changed wording falls back with `unverified_policy_wording`. This conservative restriction avoids treating an action label as proof that generated dialogue preserved the deadline or proposal. Offline use is deterministic. Freely paraphrased online dialogue remains a future improvement requiring validation.

## Synthetic demonstration

1. "I have too many tasks and 12 hours of work. Could you help me prioritise?"
2. After the manager raises the deadline: "I understand the report must be ready by Friday. Could we move the other tasks to Monday?"
3. After the manager asks for confirmation: "Agreed, I will carry out that plan."

The attempt resolves after three meaningful exchanges. Try "I don't agree" at step 3 to see the confirmation stage remain active. Pause/reload or retry the last turn to inspect recovery. These examples are synthetic engineering fixtures, not participant evidence.

## Verification

- `backend/tests/test_workload_dialogue.py`: progression, agreement rejection, cap, early finish, safety, JSON restoration, snapshot rewind, immutable completed measurements, legacy completion and online wording validation.
- `backend/tests/test_mongo_integration.py`: real MongoDB persistence, new repository/service restoration, continued negotiation and rewind, plus existing required-task coverage.
- `frontend/e2e/practice.spec.ts`: saved progress and pause/reload on desktop and mobile, including accessibility checks. This UI test uses API fixtures; it does not claim a full-stack browser demonstration.
- Existing backend tests cover account ownership, API behavior, study tasks, research exports and synthetic cohort consistency.

Verified locally: 159 backend tests passed with `TEST_MONGODB_URI=mongodb://localhost:27017`; 2 desktop/mobile browser checks passed; frontend build and lint and focused backend Ruff checks passed. Live provider calls were not used; online guard behavior was tested with a stub.
