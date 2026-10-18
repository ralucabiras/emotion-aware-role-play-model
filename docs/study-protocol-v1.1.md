# AffectLab feasibility and usability pilot protocol

**Protocol ID:** `affectlab-feasibility-v1.1`  
**Amends:** `affectlab-feasibility-v1.0`  
**Status:** Frozen before recruitment; recruitment must not begin until approval and implementation-concordance checks are complete  
**Amendment date:** 18 October 2026  
**Freeze date:** 18 October 2026  
**Design:** Single-arm, within-participant feasibility and usability pilot

Version 1.0 is preserved unchanged. This amendment was prepared before recruitment and therefore affects no enrolled participants or collected outcomes. It changes the recruitment target, clarifies the primary outcome and manual finishing, distinguishes two confidence questions, prespecifies deterministic communication indicators, documents fixed-order limitations, and clarifies versioning and withdrawal language.

Recruitment may begin only after the university ethics and supervisory requirements are satisfied, the participant information and consent materials identify this protocol version, and the deployed application and export rules have been checked against this document. The freeze records the analysis plan and does not itself represent ethics approval.

## Research question

Among English-speaking adults able to provide informed consent, is the text-based AffectLab workflow feasible and acceptable for completing three standardized difficult-conversation rehearsals, and what preliminary patterns are observed in self-reported conversation confidence and deterministic, text-derived communication indicators?

This is not a clinical-effectiveness or therapeutic-efficacy study. It cannot establish that AffectLab improves mental health, treats anxiety, causes greater communication confidence or skill, or is superior to another intervention.

## Outcomes

### Primary outcome

Protocol completion is the proportion of the enrolled set whose first required attempt for each of the three standardized scenarios:

1. matches the required scenario and intermediate difficulty;
2. reaches an eligible automatic task ending (`success` or `maximum_turns`); and
3. has a complete immediate post-rehearsal questionnaire containing confidence, realism, and feedback-usefulness ratings, each from 1 to 7.

All three scenario-level requirements must be met. Task ending and questionnaire submission are separate requirements. A questionnaire submitted after an ineligible ending does not convert that attempt into a completed primary-outcome task.

The feasibility target is at least 80% protocol completion, corresponding to at least 12 of 15 enrolled participants. Meeting this target will be interpreted only as a **preliminary feasibility signal** in this small pilot, not definitive evidence of feasibility in a broader population.

### Secondary outcomes

- Feedback-usefulness rating after each rehearsal (1–7).
- Scenario-realism rating after each rehearsal (1–7).
- Within-scenario confidence change: post-confidence minus pre-confidence for the same eligible task (1–7 items; possible change range −6 to +6).
- Pre-rehearsal confidence by ordered scenario, summarized descriptively as an across-scenario baseline-confidence pattern.
- Baseline pre-rehearsal anxiety (1–7), summarized descriptively only because no post-anxiety item is collected.
- Scenario workflow-completion rate, turn count, elapsed-time proxy, completion reason, and response generation/fallback source.
- Prespecified deterministic communication-indicator scores described below.
- Safety interruptions, technical failures, fallback use, withdrawal, and missing-questionnaire frequency.

All secondary outcomes are exploratory. The 1–7 items are study-specific feasibility/usability measures, not validated clinical scales.

## Recruitment target and precision

- Target enrollment: 15 participants.
- Target protocol completers: at least 12.
- Recruitment stops at 15 valid enrolled participants unless a documented, approved amendment is made before further enrollment.
- Enrolled set: everyone validly enrolled under the effective protocol, including participants who begin no required scenario, unless their data cannot be used under the approved withdrawal terms.
- Completer set: enrolled participants satisfying the primary-outcome definition.
- Per-task set: eligible task observations meeting the stated requirements for the relevant secondary analysis.

The target is a pragmatic compromise for an exploratory feasibility pilot; it is not an efficacy power calculation. Uncertainty remains substantial. Illustrative two-sided 95% Wilson intervals at the planned denominator are:

| Completers | Completion | 95% Wilson interval |
|---:|---:|---:|
| 9/15 | 60.0% | 35.7%–80.2% |
| 10/15 | 66.7% | 41.7%–84.8% |
| 11/15 | 73.3% | 48.0%–89.1% |
| 12/15 | 80.0% | 54.8%–93.0% |
| 13/15 | 86.7% | 62.1%–96.3% |
| 14/15 | 93.3% | 70.2%–98.8% |
| 15/15 | 100.0% | 79.6%–100.0% |

## Eligibility

### Inclusion criteria

- At least 18 years old.
- Able to read and respond in English.
- Able to understand the participant information and provide informed consent.
- Has access to a compatible web browser and can complete the study independently.
- Willing to rehearse ordinary interpersonal conversations and complete all three standardized tasks.

### Exclusion criteria

- Under 18 or unable to provide informed consent.
- Insufficient English comprehension for the tasks and questionnaires.
- Seeking diagnosis, treatment, crisis care, or emergency support from AffectLab.
- Currently in an acute crisis or reporting an immediate risk requiring emergency or clinical support.
- Prior participation under another account.
- Research-team member directly involved in developing or assessing AffectLab.

Eligibility is self-reported. Exclusion is not a clinical judgment, and the application is not a screening or diagnostic service.

## Required procedure

Participants complete the following in a fixed order, all at **intermediate** difficulty:

1. `workload`: discuss workload with a manager.
2. `boundary`: refuse a request while maintaining a boundary.
3. `relationship`: express a relationship need without blame.

Before each scenario, confidence and anxiety ratings are collected. Immediately after an automatically ended or manually finished scenario, confidence, realism, and feedback-usefulness ratings are offered. Custom scenarios, beginner/difficult levels, reflection chat, retries, branches, and additional practice remain available but are excluded from the primary outcome and labelled exploratory.

The fixed order standardizes delivery but makes scenario effects inseparable from order, interface-familiarity, fatigue, and practice effects. Higher ratings or scores in later scenarios therefore cannot be interpreted as improvement caused by repeated use.

Participants may pause, withdraw, or stop at any time. A safety interruption ends the affected task and is reported as an incomplete task with a safety-interruption reason; it is never treated as a skill failure.

### Ending and completion classifications

- `success`: eligible automatic ending for the primary task; this records that configured task conditions were reached, not real-world communication success.
- `maximum_turns`: eligible automatic workflow ending for the primary task; it does not imply that the configured skill conditions were reached.
- `user_finished`: manual stop. Post-ratings may be collected, but the task is **not** complete for the primary outcome in v1.1.
- `safety_interruption`, `unresolved`, abandonment, and technical failure: not complete for the primary outcome.

This conservative definition prevents every manual stop from being counted as primary completion. Any future rule that recognizes a predefined valid manual-ending state requires a prospective protocol and implementation amendment.

## Measurement schedule

| Time | Measures |
|---|---|
| Enrollment | Consent version/time, protocol version, pseudonymous participant ID |
| Immediately before each required scenario | Confidence 1–7; anxiety 1–7 |
| During each scenario | Scenario/difficulty, text-minimized events, message/turn count, start/end timestamps, completion reason, generation/fallback source |
| Immediately after an ended scenario | Confidence 1–7; realism 1–7; feedback usefulness 1–7; deterministic communication indicators |
| Study close or withdrawal | Completion status, missingness, withdrawal/safety/technical status |

No retrospective questionnaire completion is permitted after the participant leaves the task screen.

## Confidence analyses

Two distinct questions are retained:

1. **Within-scenario confidence change:** for each task with both ratings, calculate post-confidence minus pre-confidence. This describes immediate self-reported change associated with that rehearsal experience but does not establish causation or durable improvement.
2. **Across-scenario baseline confidence:** summarize the three pre-confidence ratings by scenario/order and, where complete, the within-participant sequence from workload to boundary to relationship. Because scenario content and order change together, this is descriptive only and is not an estimate of learning or practice benefit.

Unpaired pre- or post-confidence values remain in their respective descriptive summaries but are excluded from paired change calculations.

## Deterministic communication indicators

### General scoring rule

Indicators are produced by versioned, deterministic, case-insensitive lexical rules applied to participant rehearsal turns. They are not produced by an LLM, by the text/audio emotion model, or by a human competence judgment.

Unless an indicator below specifies a narrower eligible-turn set, its score is:

`number of eligible participant turns matching the rule / number of eligible participant turns`

Scores range from 0 to 1. A score is the frequency with which the configured wording pattern was observed; it is not a validated measure of assertiveness, empathy, communication quality, or real-world ability. Evidence-turn indices and the scoring/policy version are retained for audit. No cross-scenario composite skill score will be calculated.

### Prespecified indicators

| Scenario | Analysis indicator | Eligible turns and deterministic operational definition | Interpretation |
|---|---|---|---|
| Workload | Clear request | All participant turns; apply the `concrete_request` predicate in the locked dictionary below. | Frequency of configured request wording. |
| Workload | Specific detail | All participant turns; apply the `specific_detail` predicate below. | Frequency of configured concrete-detail wording. |
| Workload | No configured blame marker | All participant turns; match when the `blame_language` predicate below is false. | Absence of a narrow blame lexicon, not proof of collaboration. |
| Boundary | Clear refusal or maintained boundary | All participant turns; apply the `maintained_boundary` predicate below. | Frequency of configured refusal wording. The current exported labels `clear refusal` and `boundary maintenance` use the same predicate and will be treated as one underlying indicator, not two independent findings. |
| Boundary | No repeated apology | All participant turns; match when no more than one occurrence of “sorry” or `apologise/apologize` appears in the turn. | Absence of repeated apology wording; not a general measure of concision. |
| Relationship | I-statement | All participant turns; apply the `i_statement` predicate below. | Frequency of configured first-person wording. |
| Relationship | Specific detail | All participant turns; apply the `specific_detail` predicate below. The stored display label may be `specific need`. | Frequency of concrete-detail wording, not proof that a need was communicated effectively. |
| Relationship | No configured blame marker | All participant turns; match when the `blame_language` predicate below is false. | Absence of a narrow blame lexicon, not proof of a non-blaming interaction. |

### Locked lexical dictionary for v1.1 concordance

Text is converted to lowercase before these predicates are evaluated. Quoted values are literal substring matches unless a regular expression is shown.

- `concrete_request = true` when the turn contains at least one of: `i need`, `i want`, `i would like`, `could you`, `please`, `i can't`, `i cannot`, or `no,`.
- `maintained_boundary = true` when the turn contains at least one of: `i can't`, `i cannot`, `i won't`, `not able`, `my boundary`, or `i need to say no`.
- `blame_language = true` when the turn contains at least one of: `you always`, `you never`, `you don't`, `your fault`, or `you make me`.
- `specific_detail = true` when the turn contains at least one of: `deadline`, `because`, `when `, `this week`, `priority`, `specifically`, `each week`, `per week`, `evening`, `weekend`, `minutes`, `hours`, `meeting`, `interrupt`, `chores`, `dishes`, `cleaning`, `monday`, `tuesday`, `wednesday`, `thursday`, or `friday`; or when it matches the regular expression `\b\d+\b`.
- `i_statement = true` when the turn matches the regular expression `\bi (?:feel|need|want|would like|am)\b`.
- `excessive_apology = true` when the regular expression `\b(sorry|apologi[sz]e)\b` occurs more than once in the turn. The analysis indicator `no repeated apology` is the logical inverse.

The exact scoring dictionary, regular expressions, eligible-turn logic, and version identifier must be frozen in the analysis materials before enrollment. A concordance test must confirm that deployed feedback, stored numeric metrics, and the frozen analysis specification produce the same values on fixed examples.

Each required scenario supplies only one post-rehearsal set of communication indicators and has no pre-rehearsal behavioral score. Therefore, the required protocol does not estimate within-scenario skill improvement. Metrics from different scenarios measure different constructs and will not be compared as if they formed a common improvement scale. Repeated optional practice of the same scenario may be summarized separately as exploratory, self-selected activity, with attempt number and scoring version reported.

## Missing and invalid data

- Primary analysis uses the enrolled set. A participant who begins no required task, or who begins a task but does not satisfy the full completion definition, is a non-completer unless their data cannot be used under the approved withdrawal terms; no completion data are imputed.
- Only the first explicitly required attempt for each task is used for the primary outcome. Retries and additional practice cannot replace it.
- Questionnaire and communication-indicator summaries use available eligible observations and report the denominator for every result.
- Paired confidence change requires pre- and post-confidence from the same eligible task.
- No mean substitution, last-observation-carried-forward, or model-based imputation is planned.
- Duplicate accounts, tests, researcher accounts, data recorded before consent, and records excluded under documented data-quality rules are excluded.
- Technical failures and safety interruptions are retained as feasibility outcomes but are not assigned questionnaire or communication-indicator values when those values were not observed.
- Reasons for missingness are tabulated where observable: participant stopped, manual finish, withdrawal, safety interruption, technical failure, questionnaire skipped/closed, or unknown.

## Statistical analysis plan

1. Report enrollment, task flow, exclusions, withdrawals, and missingness in a participant-flow table.
2. Estimate the primary completion proportion with a two-sided 95% Wilson confidence interval and compare it descriptively with the 80% target. The target is a decision aid and preliminary signal, not a null-hypothesis efficacy test.
3. Summarize ordinal 1–7 ratings using count, median, interquartile range, mean, standard deviation, and range.
4. Summarize within-scenario paired confidence changes overall and by scenario. Report the count and median change with a participant-cluster bootstrap 95% confidence interval. A Wilcoxon signed-rank test may be reported as exploratory only when at least ten non-zero paired differences are available.
5. Summarize pre-confidence across the three fixed-order scenarios descriptively. Do not interpret changes as practice effects. No inferential across-scenario baseline-confidence test is planned.
6. Summarize each deterministic communication indicator within its eligible scenario, together with its scoring version and denominator. Do not pool unlike indicators or interpret cross-scenario differences as improvement.
7. Summarize turn counts, elapsed-time proxies, completion reasons, manual finishes, safety interruptions, fallback rates, generation sources, and questionnaire missingness descriptively.
8. Any scenario comparisons are exploratory and confounded by fixed order. If an unplanned inferential comparison is reported, label it as such, justify it, and apply appropriate multiplicity control; do not rely on p-values alone.
9. Do not infer therapeutic benefit, diagnostic validity, causal effectiveness, sustained learning, or transfer to real conversations. No subgroup inferential analysis is planned for this sample size.

Analysis scripts must use pseudonymous frozen exports, record the protocol and scoring versions, export checksum and timestamp, and report all deviations from this plan.

## Role of multimodal affect inference

The core intervention is the text-based adaptive reflection and role-play workflow with deterministic safety and feedback rules. Optional voice transcription is an input convenience. The trained text/audio fusion affect model is an **exploratory component only**:

- Voice is optional and absence of audio does not affect protocol completion.
- Multimodal estimates do not determine eligibility, primary outcomes, safety escalation, scenario success, or communication-indicator scores.
- Model outputs may be summarized separately for coverage, confidence, agreement, latency, and failure rate when available.
- No claim about emotion-recognition effectiveness on participants is made without ground-truth labels and a separately approved analysis.

## Protocol and analysis versioning

Participants consent to the approved study procedures and data uses described in their participant-facing materials. Protocol, scoring, export, and analysis-plan versions are tracked separately. A post-approval change must be documented with its date, rationale, affected data/outcomes, and ethics/supervisory determination.

An analysis clarification does not automatically require participant re-consent. Re-consent is required only when the applicable ethics decision, consent terms, or law requires it—for example, when a change materially affects participation, risks, or data use. Analyses must use the protocol applicable to each participant and clearly report any version differences.

## Governance and withdrawal

Study records follow the approved participant information, consent terms, retention schedule, ethics decision, and applicable data-protection requirements. Records remain pseudonymous rather than anonymous while a withdrawal link is retained. Withdrawal from further participation does not automatically imply that every previously collected record must be deleted: prior data will be retained, excluded, anonymized, or deleted according to the approved consent and withdrawal terms and any point after which removal is no longer feasible. The participant-facing materials must state these consequences clearly before recruitment.

Research exports exclude account identity, conversation text, raw audio, custom wording, and saved takeaways. University ethics approval, supervisor confirmation, participant-facing contacts, the final retention statement, withdrawal handling, and implementation-concordance checks must be completed before recruitment.
