# AffectLab feasibility and usability pilot protocol

**Protocol ID:** `affectlab-feasibility-v1.0`  
**Status:** Frozen before recruitment  
**Freeze date:** 22 September 2026  
**Design:** Single-arm, within-participant feasibility and usability pilot

Changes after recruitment starts must produce a new protocol version, state the reason, identify affected participants and outcomes, and preserve this document unchanged. Confirmatory interpretations may use only the version participants consented to.

## Research question

Among English-speaking adults able to provide informed consent, is the text-based AffectLab workflow feasible and acceptable for completing three standardized difficult-conversation rehearsals, and what preliminary changes in self-reported conversation confidence and observable communication-skill metrics occur across those rehearsals?

This is not a clinical-effectiveness or therapeutic-efficacy study. It cannot establish that AffectLab improves mental health, treats anxiety, or is superior to another intervention.

## Outcomes

### Primary outcome

Protocol completion: the proportion of enrolled participants who complete all three required standardized scenarios at intermediate difficulty and submit the post-rehearsal questionnaire for each. The feasibility target is at least 80% completion (24 of 30 if exactly 30 enroll).

### Secondary outcomes

- Mean and median feedback-usefulness rating after each rehearsal (1–7).
- Mean and median scenario-realism rating after each rehearsal (1–7).
- Within-rehearsal change in conversation confidence: post-confidence minus pre-confidence (1–7).
- Baseline pre-rehearsal anxiety (1–7), summarized descriptively only because no post-anxiety item is collected.
- Scenario completion rate, number of turns, completion reason, and template/OpenAI generation source.
- Deterministic communication-skill scores and within-participant changes where the same metric is observed more than once.
- Safety interruptions, technical failures, fallback use, withdrawal, and missing-questionnaire frequency.

All secondary outcomes are exploratory. The 1–7 items are study-specific feasibility/usability measures, not validated clinical scales.

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

## Recruitment target and analysis populations

- Target enrollment: 30 participants.
- Target protocol completers: at least 24.
- Recruitment stops at 30 valid enrolled participants unless a documented amendment is approved before additional enrollment.
- Enrolled set: everyone who provides the current protocol consent and begins at least one required scenario.
- Completer set: enrolled participants satisfying the primary outcome definition.
- Per-task set: all eligible completed task/questionnaire pairs for the relevant secondary analysis.

This target estimates operational feasibility and provides preliminary distributions; it is not an efficacy power calculation.

## Required procedure

Participants complete the following in order, all at **intermediate** difficulty:

1. `workload`: discuss workload with a manager.
2. `boundary`: refuse a request while maintaining a boundary.
3. `relationship`: express a relationship need without blame.

Before each scenario, collect confidence and anxiety ratings. After each completed or manually finished scenario, collect confidence, realism, and feedback-usefulness ratings. Custom scenarios, beginner/difficult levels, reflection chat, retries, and additional practice remain available but are excluded from the primary outcome and labelled exploratory.

Participants may pause, withdraw, or stop at any time. A safety interruption ends the affected task and is reported as an incomplete task with a safety-interruption completion reason; it is never treated as a skill failure.

## Measurement schedule

| Time | Measures |
|---|---|
| Enrollment | Consent version/time, protocol version, pseudonymous participant ID |
| Immediately before each required scenario | Confidence 1–7; anxiety 1–7 |
| During each scenario | Scenario/difficulty, text-free events, turn count, completion reason, generation/fallback source |
| Immediately after each required scenario | Confidence 1–7; realism 1–7; feedback usefulness 1–7; deterministic skill metrics |
| Study close or withdrawal | Completion status, missingness, withdrawal/safety/technical status |

No retrospective questionnaire completion is permitted after the participant leaves the task screen.

## Missing and invalid data

- Primary analysis uses the enrolled set. Anyone who starts a required task but does not satisfy the full completion definition is a non-completer; no completion data are imputed.
- Questionnaire and skill summaries use available eligible observations and report the denominator for every result.
- Paired confidence change requires both pre- and post-confidence for the same eligible task. Unpaired values remain in descriptive summaries but not paired analyses.
- No mean substitution, last-observation-carried-forward, or model-based imputation is planned.
- Duplicate accounts, tests, researcher accounts, data recorded before consent, and records from withdrawn participants are excluded.
- Technical failures and safety interruptions are retained as feasibility outcomes but are not assigned questionnaire or skill values.
- Reasons for missingness are tabulated where observable: participant stopped, withdrawal, safety interruption, technical failure, or unknown.

## Statistical analysis plan

1. Report enrollment, task flow, exclusions, withdrawals, and missingness in a participant-flow table.
2. Estimate primary completion proportion with a two-sided 95% Wilson confidence interval and compare descriptively with the 80% feasibility target. This is a decision threshold, not a null-hypothesis efficacy test.
3. Summarize ordinal 1–7 ratings using count, median, interquartile range, mean, standard deviation, and range.
4. Summarize paired confidence changes overall and by scenario. Report median change and a participant-cluster bootstrap 95% confidence interval. A Wilcoxon signed-rank test may be reported as exploratory when at least ten non-zero paired differences are available.
5. Summarize deterministic skill metrics, task duration proxies/turn counts, completion reasons, safety interruptions, fallback rates, and generation sources descriptively.
6. Scenario comparisons are exploratory. If tested, use a Friedman test for complete within-participant observations followed by Holm-adjusted paired comparisons. Report effect estimates and intervals, not only p-values.
7. Do not infer therapeutic benefit, diagnostic validity, or causal effectiveness. No subgroup inferential analysis is planned for this sample size.

Analysis scripts must use pseudonymous frozen exports, record the export checksum and timestamp, and report deviations from this plan.

## Role of multimodal affect inference

The core intervention is the text-based adaptive reflection and role-play workflow with deterministic safety and feedback rules. Optional voice transcription is an input convenience. The trained text/audio fusion affect model is an **exploratory component only**:

- Voice is optional and absence of audio does not affect protocol completion.
- Multimodal estimates do not determine eligibility, primary outcomes, safety escalation, scenario success, or feedback scores.
- Model outputs may be summarized separately for coverage, confidence, agreement, latency, and failure rate when available.
- No claim about emotion-recognition effectiveness on participants is made without ground-truth labels and a separately approved analysis.

## Governance

Study records follow the configured explicit retention period, remain pseudonymous rather than anonymous while linked for withdrawal, and are excluded/deleted on withdrawal where still identifiable. Research exports exclude account identity and conversation text. University ethics approval, supervisor confirmation, participant-facing contacts, and the final retention statement must be completed before recruitment.

