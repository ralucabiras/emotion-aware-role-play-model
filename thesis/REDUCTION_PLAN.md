# Dissertation Reduction Plan

Last updated: 2026-10-22  
Overall status: Chapters 1 and 3 complete and verified; Chapter 4 rewrite next
Coordinator guidance: approximately **30--40 pages of content**, excluding the covers, abstract, table of contents, bibliography, and appendices  
Working target: **36--37 pages of numbered chapter content**  
Hard ceiling: **40 pages of numbered chapter content**

## Purpose of this document

This is the living tracker for reducing the dissertation. It should be updated after every editing session so that the current page count, completed work, decisions, and next action remain clear.

The reduction must preserve the research argument and evidence. Detailed software documentation, supplementary experiments, and exhaustive verification records should move to appendices or remain in the repository rather than occupying the main chapters.

## Status legend

- `[ ]` Not started
- `[~]` In progress
- `[x]` Complete and checked
- `[!]` Blocked or awaiting a decision

## Baseline and target

The baseline PDF contains 161 physical pages. Based on its table of contents, the six numbered chapters occupy approximately 140 pages, including chapter-opening layout and intervening blank pages. At the initial audit, the chapter sources contained approximately 53,155 source words; this count includes some LaTeX and table content and is therefore an approximate tracking measure rather than a polished-prose count. After the Chapter 1 and Chapter 3 rewrites, the estimated current total is approximately 40,147 source words.

| Part | Baseline pages | Baseline source words | Target pages | Target words | Status |
|---|---:|---:|---:|---:|---|
| Chapter 1: Introduction | 22 | 8,232 | 4 | 1,400--1,600 | `[x]` |
| Chapter 2: State of the Art | 18 | 6,860 | 6 | 2,300--2,600 | `[ ]` |
| Chapter 3: Proposed System Architecture | 22 | 7,889 | 5 | 1,700--2,000 | `[x]` |
| Chapter 4: Implementation | 46 | 16,934 | 8 | 3,000--3,500 | `[ ]` |
| Chapter 5: Evaluation and Results | 22 | 9,289 | 10--11 | 4,000--4,500 | `[ ]` |
| Chapter 6: Conclusions and Future Work | 10 | 3,951 | 3 | 1,000--1,300 | `[ ]` |
| **Total main content** | **about 140** | **53,155** | **36--37** | **13,400--15,500** | `[ ]` |

The working target deliberately stays below 40 pages to allow for LaTeX reflow, figures, tables, and chapter-opening whitespace.

## Content ownership rules

Each topic should have one authoritative location. Other chapters may refer to it briefly, but should not repeat its explanation.

| Topic | Authoritative location |
|---|---|
| Prior research and research gap | Chapter 2 |
| System architecture and design requirements | Chapter 3 |
| Implementation mechanisms | Chapter 4 |
| Experimental protocol, numerical results, tests, and threats to validity | Chapter 5 |
| Final answers, implications, and future work | Chapter 6 |
| Complete requirements, secondary results, and detailed verification evidence | Appendices |
| Routine software details | Repository documentation only |

The abstract may state headline results and essential caveats, but the numbered chapters should not repeat the same figures in several places.

## Material that must be protected

- The aim, objectives, and four research questions.
- The literature needed to justify the research gap and chosen methods.
- The distinction between affect inference and authoritative dialogue, safety, and feedback decisions.
- The primary four-class, speaker-independent evaluation protocol.
- The principal contextual-text, audio, fusion, and calibration results.
- Enough implementation detail to understand the original contribution.
- Evidence supporting the application-quality claims.
- The pilot's actual scope and its most important limitation.
- Ethical, privacy, safety, and generalisation boundaries.
- A clear threats-to-validity discussion.

## Main-text, appendix, or delete rule

Use the following test whenever a paragraph, table, or figure is reviewed:

1. **Keep in the main text** if it is required to understand, evaluate, or defend the central research contribution.
2. **Move to an appendix** if it provides useful reproducibility or supporting evidence but is not required to follow the argument.
3. **Keep only in repository documentation** if it describes routine implementation or operational detail.
4. **Delete entirely** if it duplicates another passage, restates a table, provides obsolete detail, or supports no dissertation claim.

Moving material to an appendix is not the default. The appendices should remain selective rather than becoming a relocated version of the original thesis.

## Phase 0: Establish the evidence source of truth

- [x] Extract the final numerical claims from Chapter 5 into a short working checklist.
- [x] Record which tables and figures directly support RQ1--RQ4.
- [x] Mark Chapter 5 as the authoritative source for scores, test counts, pilot results, and limitations.
- [x] Identify any results in the abstract that no longer match Chapter 5.
- [x] Check the current Faculty of Informatics completion page and the standardised thesis template for chapter-summary, list, and appendix expectations.

Completion condition: all essential claims and their supporting evidence are known before duplicated passages are removed elsewhere.

### Frozen evidence checklist

Chapter 5 is the source of truth for every score, test count, pilot result, and limitation below. Later chapters may summarise the conclusion but must not introduce a different value or a stronger interpretation.

#### Model protocol and principal results

- [x] Primary task: 5,531 matched text--audio utterances from 151 dialogues, four classes, and five speaker-independent IEMOCAP session folds; one session is held out for test and another for validation in each fold.
- [x] RQ1 headline: three-turn causal context improved accuracy from 0.6624 to 0.7304, macro F1 from 0.6651 to 0.7332, and weighted F1 from 0.6640 to 0.7300. The macro-F1 difference was +0.0681 with a dialogue-bootstrap 95\% interval of 0.0504--0.0857.
- [x] Audio baseline: accuracy 0.6279, macro F1 0.6349, weighted F1 0.6229, and ECE 0.0468.
- [x] RQ2 classification headline: predeclared equal-weight fusion reached accuracy 0.7832, macro F1 0.7883, and weighted F1 0.7815. Its macro-F1 improvement over contextual text was +0.0551 with a 95\% interval of 0.0407--0.0713; all 10,000 dialogue-bootstrap replicates favoured fusion on the three aggregate metrics.
- [x] Calibration trade-off: contextual text ECE was 0.0311; equal fusion ECE was 0.1619; fold-specific validation-fitted fusion reduced ECE to 0.0283 while retaining accuracy 0.7717 and macro F1 0.7758. Classification and calibration must remain separate claims.
- [x] Operational packaging: the global chain selected text/audio weights 0.59/0.41 and temperature 0.5989. Its macro F1 0.7776 and ECE 0.0242 are label-reused descriptive values, not independent held-out evidence.
- [x] The exploratory six-class experiment is secondary evidence only: 7,420 examples, macro F1 0.5490 to 0.6222, but only 40 mapped anxiety examples. It must not support a deployed anxiety-recognition claim.

#### Application-verification claims

- [x] RQ3 policy evidence: all five authored enhanced-dialogue trajectories and all seven controlled affect-pacing cases matched their declared outcomes. Twelve diagnostic extraction cases produced five true positives, four true negatives, one false positive, and two false negatives; these are examples, not an accuracy estimate.
- [x] Cognitive/support-routing cases establish rule conformance only; they do not establish psychological construct validity, clinical validity, comparative helpfulness, or absence of harm.
- [x] RQ4 automated evidence: 258 backend cases were collected, with 245 passes and 13 explicitly identified real-MongoDB skips; Ruff, the production frontend build, and frontend linting passed.
- [x] Browser evidence: 38 logical cases across desktop Chromium and a Pixel 7 profile produced 76 passes; 10 interface states in both projects produced 20 axe scans with zero detected violations. This is not WCAG certification.
- [x] Full-stack evidence: two compiled-frontend/FastAPI/MongoDB smoke journeys passed, including persistence checks across two backend restarts. Live providers and trained inference were disabled.
- [x] Local performance evidence: all five regression budgets passed. The deterministic conversation turn had median 4.659 ms and P95 5.836 ms. The in-process, single-client benchmark excludes network transit, MongoDB, trained inference, providers, and concurrency.

#### Supplementary pilot claims

- [x] Fifteen participants were included; 12 completed all three required tasks and questionnaires, giving 80.0\% protocol completion with a 95\% Wilson interval of 54.8\%--93.0\%.
- [x] The first-required-attempt export contained 42 required attempts, 39 completed tasks, and 40 available realism/usefulness ratings. Scenario realism averaged 4.85/7 (median 5), and feedback usefulness averaged 5.33/7 (median 5).
- [x] Thirty-eight paired ratings from 14 participants produced a mean immediate confidence change of +0.97 and median +1, with a participant-cluster bootstrap 95\% interval of +0.67 to +1.26.
- [x] Required tasks bypassed multimodal inference and affect-aware pacing. The pilot describes the baseline deterministic workflow only and cannot establish adaptation benefit, causal benefit, sustained skill acquisition, or transfer to real conversations.

#### Limitations that must survive reduction

- [x] IEMOCAP contains ten actors and acted or improvised English dialogue; speaker-independent folds prevent identity leakage but do not provide external, demographic, cultural, device, or deployment validation.
- [x] Emotion labels are annotated expressive categories rather than direct measurements of internal state; thresholds of 0.55 and 0.75 are operational presentation settings rather than psychological boundaries.
- [x] One primary training seed leaves optimisation variance incompletely characterised; ECE is bin-dependent and calibration can deteriorate under domain shift.
- [x] Full-data packages have no independent test partition, and private model-file provenance remains incomplete.
- [x] Deterministic lexical feedback and cognitive fields are auditable implementation constructs, not validated measures of general communication ability, cognition, intent, cause, readiness, resistance, or clinical state.
- [x] Engineering tests use controlled inputs and synthetic accounts; they do not establish live-provider behaviour, trained-model latency, real-microphone robustness, concurrent capacity, production security, or human benefit.
- [x] The pilot is small, single-arm, uncontrolled, incomplete in places, and uses study-specific ordinal ratings; no causal or generalisable effectiveness claim is permitted.

#### Direct evidence retained for each research question

| Research question | Principal Chapter 5 evidence to retain in the main text | Secondary material suitable for an appendix or deletion |
|---|---|---|
| RQ1 | `tab:context-text-results`; four-class protocol and paired dialogue-bootstrap method; context limitation paragraph | `tab:context-text-per-class`; all six-class tables; illustrative error cases |
| RQ2 | `tab:equal-fusion-results`; `tab:calibration-tradeoff`; `fig:model-results` or one equivalent combined visual | Full per-class/fold tables; confusion matrices; reliability curves if the combined visual and prose preserve the claim; global-packaging detail; published-score comparison |
| RQ3 | Concise authored-policy aggregate covering five dialogue and seven affect cases; bounded-policy and failure/safety interpretation | Detailed trajectory, cognitive-routing, and diagnostic-case tables; exhaustive traceability rows |
| RQ4 | One aggregate verification table; scoped backend/browser/accessibility/full-stack totals; concise local P95 result and deployment caveat | Commands, node IDs, environment inventory, individual latency rows, and full requirement-to-test traceability |

The pilot is supplementary and does not answer RQ1--RQ4 directly. Its completion, median realism/usefulness, and non-adaptive-scope caveat should remain together.

#### Abstract and format audit

- [x] The abstract matches Chapter 5 for contextual-text macro F1, equal-fusion macro F1 and accuracy, the fusion improvement interval, equal-fusion ECE, 245 backend passes, 76 browser cases, two full-stack journeys, 5.836 ms local P95, participant completion, and median realism/usefulness. No numerical correction is currently required.
- [x] The abstract already states the decisive pilot limitation and the need for target-environment validation. Keep those qualifications when later prose is reduced.
- [x] The Faculty of Informatics [2025--2026 master-completion page](https://info.uvt.ro/en/finalizarea-studiilor-universitare-master/) links a standardised English LaTeX template. The local copy of that template includes a table of contents, List of Figures, List of Tables, and standard `\\appendix` handling, so retain those structures unless the supervisor directs otherwise.
- [x] No accessible official instruction or template command requires chapter-end summaries. They may therefore be removed where the plan calls for removal, subject to supervisor confirmation of any programme-specific unpublished rule.

## Chapter 1: Introduction -- target 4 pages

Planned structure:

1. Context and problem: approximately 1 page.
2. Aim and objectives: approximately 0.5 page.
3. Research questions: approximately 0.5 page.
4. Proposed approach and contributions: approximately 1.5 pages.
5. Scope and dissertation structure: approximately 0.5 page.

Tasks:

- [x] Rewrite Context and Motivation as a short problem-led opening.
- [x] Remove literature discussion of role-play, IMBUE, IEMOCAP, emotion theory, and calibration; retain it only in Chapter 2.
- [x] Merge Aim and Objectives into a compact section.
- [x] Preserve the four research questions without extended commentary.
- [x] Replace the five Proposed Approach subsections with a compact overview.
- [x] Reduce Contributions to four or five concrete contributions.
- [x] Replace the ten Scope and Limitations subsections with one short scope section.
- [x] Remove numerical results, test counts, and detailed implementation descriptions.
- [x] Reduce Dissertation Structure to one paragraph.
- [x] Verify that no claim is stronger than the evidence later presented in Chapter 5.

Completion condition: a reader can understand the problem, questions, approach, contribution, and scope without receiving a preview of every later chapter.

Current result: the chapter has five sections and 1,401 words by `texcount`, within the 1,400--1,600-word target. A clean `latexmk` build places Chapter 1 on numbered pages 1--4 and Chapter 2 on page 5. The regenerated table of contents and lists are current, the final log contains no undefined citations or references or LaTeX errors, and visual inspection of all four rendered pages found no clipping, overflow, or poor list/page breaks.

## Chapter 2: State of the Art -- target 6 pages

Planned structure:

1. Communication rehearsal, role-play, and feedback.
2. Deterministic and generative conversational agents.
3. Contextual text and speech emotion recognition.
4. Multimodal fusion, calibration, and uncertainty.
5. Research gap and design implications for AffectLab.

Tasks:

- [ ] Merge the many short subsections into the five themes above.
- [ ] Retain only literature that directly motivates a research question or design decision.
- [ ] Compress textbook-style explanations of BERT, wav2vec, emotion taxonomies, and calibration.
- [ ] Remove or move the secondary-dataset catalogue and comparison table.
- [ ] Reduce legal, privacy, and safety literature to the constraints relevant to the design.
- [ ] Remove descriptions of AffectLab implementation that belong in Chapters 3 and 4.
- [ ] Replace the large synthesis table with concise prose unless it adds unique comparative value.
- [ ] End with a precise integration-and-evaluation research gap.
- [ ] Keep the chapter summary to one short paragraph or remove it if permitted.

Completion condition: every retained source contributes directly to the research gap, method, or design rationale.

## Chapter 3: Proposed System Architecture -- target 5 pages

Planned structure:

1. Architecture and design principles: approximately 2 pages.
2. Grouped functional and non-functional requirements: approximately 1 page.
3. Dialogue, affect adaptation, and safety boundaries: approximately 1 page.
4. Ethics, privacy, and limitations: approximately 1 page.

Tasks:

- [x] Keep one principal architecture diagram.
- [x] Explain the separation between inference, dialogue control, generation, feedback, and safety once.
- [x] Replace 29 functional and 14 non-functional requirement descriptions with 8--10 grouped requirements.
- [~] Move the complete requirement list to an appendix. The 43 atomic requirements are designated for Appendix B; insertion is deferred to the appendix phase.
- [x] Merge scope, assumptions, and boundaries into a concise passage or table.
- [x] Reduce the ethics section to the safeguards that materially shaped the architecture.
- [x] Remove the detailed Limitations of the Proposed System subsections; consolidate empirical limitations in Chapter 5.
- [x] Remove repeated pilot, IEMOCAP, generative-AI, and deployment caveats.
- [x] Remove the repetitive chapter summary.

Completion condition: the chapter explains why the architecture is structured as it is without duplicating implementation or evaluation material.

Current result: the chapter has the planned four sections, one architecture figure, and one table containing nine grouped requirement families. It contains 1,712 words by `texcount`, down from the 7,889-word baseline, and occupies numbered pages 23--27. Chapter 4 begins on page 29 after the standard template's intentional blank verso. A clean `latexmk` build contains no undefined citations or references, LaTeX errors, or Chapter 3 overfull boxes; visual inspection of all five content pages found the diagram and table legible with no clipping or poor page breaks. The full 43-item requirement wording is identified for Appendix B but has not yet been inserted.

## Chapter 4: Implementation -- target 8 pages

Planned structure:

1. Technology and application overview: approximately 0.5 page.
2. Emotion-recognition pipeline: approximately 1.5 pages.
3. Backend and request processing: approximately 1.5 pages.
4. Role-play and affect-adaptation engine: approximately 2 pages.
5. Feedback and frontend workflow: approximately 1.5 pages.
6. Security, persistence, and deployment: approximately 1 page.

Tasks:

- [ ] Replace the technology inventory with a short stack overview.
- [ ] Remove repository-structure and configuration-file narration.
- [ ] Keep implementation choices that distinguish the contextual text, speech, fusion, calibration, and inference pipeline.
- [ ] Remove evaluation-protocol repetition; the definitive protocol belongs in Chapter 5.
- [ ] Condense domain models and API schemas to their architectural role.
- [ ] Remove routine authentication and account-management mechanics.
- [ ] Keep one concise request-processing description and its sequence diagram.
- [ ] Preserve the deterministic dialogue, evidence-extraction, and affect-pacing mechanisms.
- [ ] Condense feedback, replay, branching, and action cards into one section.
- [ ] Replace multiple interface screenshots with one combined figure or one representative screen.
- [ ] Reduce optional research-support implementation to one paragraph.
- [ ] Reduce security, privacy, and deployment controls to the decisions relevant to the dissertation contribution.
- [ ] Remove the Implementation Verification section; evaluation results belong in Chapter 5.
- [ ] Remove the repetitive chapter summary.

Main-text visual budget:

- [ ] Emotion pipeline.
- [ ] Request sequence.
- [ ] Dialogue-state or affect-policy diagram; retain one unless both are essential.
- [ ] One combined or representative interface figure.

Candidates for appendix or repository documentation:

- [ ] Complete repository and configuration description.
- [ ] Detailed API/domain-model information.
- [ ] Research-data lifecycle diagram.
- [ ] Deployment topology.
- [ ] Additional screenshots.
- [ ] Detailed test architecture and provenance procedures.

Completion condition: the chapter explains the technically original implementation choices, not every implemented feature.

## Chapter 5: Evaluation and Results -- target 10--11 pages

Planned structure:

1. Evaluation methodology: approximately 2 pages.
2. Contextual-text results: approximately 1.5 pages.
3. Speech, fusion, and calibration results: approximately 3 pages.
4. Application verification: approximately 1.5--2 pages.
5. Pilot results: approximately 1 page.
6. Threats to validity: approximately 1 page.

Tasks:

- [ ] Retain the speaker-independent task, folds, metrics, and dialogue-level statistical comparison.
- [ ] Retain the primary four-class contextual-text experiment.
- [ ] Retain the audio, equal-weight fusion, and calibration trade-off results.
- [ ] Select only the tables and figures required to support the principal claims.
- [ ] Move the exploratory six-class experiment to an appendix.
- [ ] Move full per-class and per-fold tables to an appendix.
- [ ] Reduce the operational packaging analysis to one short paragraph or move it.
- [ ] Condense the comparison with published IEMOCAP results.
- [ ] Replace detailed authored-case and test-suite tables with one aggregate verification table.
- [ ] Move the complete requirement-to-test traceability matrix to an appendix.
- [ ] Report exact test counts once.
- [ ] Keep the pilot results and state their scope limitation once, immediately beside them.
- [ ] Consolidate model, construct, external, pilot, and application limitations in Threats to Validity.
- [ ] Remove the separate Answer to RQ1--RQ4 subsections; final answers belong in Chapter 6.
- [ ] Remove or reduce the chapter summary to a transition paragraph.

Completion condition: every principal conclusion is supported by visible evidence, while secondary and audit-level evidence remains available outside the main narrative.

## Chapter 6: Conclusions and Future Work -- target 3 pages

Planned structure:

1. Direct answers to RQ1--RQ4: approximately 1.5 pages.
2. Contributions and limitations: approximately 0.75 page.
3. Prioritised future work: approximately 0.5 page.
4. Final conclusion: approximately 0.25 page.

Tasks:

- [ ] Delete Chapter Overview.
- [ ] Delete the long Summary of the Dissertation.
- [ ] Answer the four research questions in compact paragraphs or one table.
- [ ] Merge the three contribution subsections.
- [ ] Summarise only the limitations that materially qualify the final conclusions.
- [ ] Keep the future-work roadmap but remove the six subsections that restate it.
- [ ] Avoid repeating detailed scores, test counts, and implementation descriptions.
- [ ] End with one restrained conclusion paragraph.

Completion condition: the chapter answers the research questions and states what the work establishes without summarising the dissertation chapter by chapter.

## Appendices plan

Appendices do not count toward the coordinator's recommended 30--40 content pages, but they should remain concise and useful.

| Appendix | Proposed contents | Status |
|---|---|---|
| A | Generative AI declaration, reduced to the required disclosure | `[ ]` |
| B | Complete functional and non-functional requirements | `[~]` Identified from the former Chapter 3 inventory; insertion deferred to the appendix phase |
| C | Supplementary model results: six-class, per-class, and per-fold tables | `[ ]` |
| D | Application-verification details and requirement traceability | `[ ]` |
| E | Additional interface or deployment figures, only if required | `[ ]` |

Items should not be moved automatically. Each proposed appendix item must first pass the reproducibility/supporting-evidence test.

## Repetition-removal checklist

The following claims currently recur across several chapters. Retain the full explanation only in the location shown.

- [ ] IEMOCAP generalisation limits -- Chapter 5 Threats to Validity.
- [ ] Affect predictions are bounded signals, not true internal states -- Chapter 3.
- [ ] Safety is independent of the emotion classifier -- Chapter 3, with implementation detail in Chapter 4.
- [ ] Classification and calibration are separate concerns -- Chapter 2 conceptually and Chapter 5 empirically.
- [ ] Required pilot tasks bypassed multimodal adaptation -- Chapter 5 beside the pilot result.
- [ ] The pilot cannot establish causal benefit -- Chapter 5.
- [ ] Exact model scores -- Chapter 5, plus headline values in the abstract.
- [ ] Exact automated-test counts -- Chapter 5, plus at most one headline statement in the abstract.
- [ ] Deployment validation remains necessary -- Chapter 5 limitations and one sentence in Chapter 6.
- [ ] Audio minimisation and provider boundaries -- Chapter 4.

## Execution order

- [x] Phase 0: freeze the evidence and principal claims from Chapter 5.
- [x] Rewrite and verify Chapter 1.
- [x] Rewrite and verify Chapter 3.
- [ ] Rewrite Chapter 4.
- [ ] Condense Chapter 2.
- [ ] Refine Chapter 5 and extract appendix material.
- [ ] Rewrite Chapter 6.
- [ ] Reduce the AI-use appendix and organise supplementary appendices.
- [ ] Recompile and measure numbered chapter pages.
- [ ] Perform a final cross-reference, citation, terminology, and claim-strength audit.

## Quality gates

### After each chapter

- [ ] The chapter is within its page and word budget.
- [ ] Every section contributes directly to a research question, design decision, result, or conclusion.
- [ ] No paragraph substantially duplicates another chapter.
- [ ] Figures and tables are interpreted in prose rather than restated cell by cell.
- [ ] Cross-references still resolve.
- [ ] Claims remain proportionate to the evidence.

### Before final submission

- [ ] Numbered Chapters 1--6 total no more than 40 pages.
- [ ] Working target of 36--37 pages is achieved where possible.
- [ ] Abstract matches the final results and limitations.
- [ ] All four research questions are answered directly.
- [ ] Every retained figure and table is cited and necessary.
- [ ] Bibliography contains no orphaned entries caused by deleted text, where practical to check.
- [ ] Appendix references resolve correctly.
- [ ] Table of contents and lists are regenerated.
- [ ] No accidental blank pages inflate the content count.
- [ ] Final PDF receives a complete visual check.

## Progress log

| Date | Work completed | Result | Next action |
|---|---|---|---|
| 2026-10-21 | Audited the 161-page PDF, six chapter sources, heading structure, page distribution, figures, tables, and major cross-chapter repetition. | Identified Chapters 1, 3, and 4 as the largest structural-cut opportunities; Chapter 5 should be protected as the evidence centre. | Update the plan after receiving the coordinator's expected length. |
| 2026-10-22 | Incorporated the coordinator's recommendation of approximately 30--40 content pages and created this living tracker. | Set a 36--37-page working target and chapter-level budgets. No dissertation content changed. | Complete Phase 0 by freezing the essential Chapter 5 claims and evidence. |
| 2026-10-22 | Completed the Phase 0 evidence freeze from Chapter 5, mapped the principal evidence to RQ1--RQ4, audited the abstract, and checked the Faculty's 2025--2026 completion page and local standardised template. | Established a source-of-truth checklist for model, application, pilot, and limitation claims. The abstract requires no numerical correction. Retain the Lists of Figures/Tables and appendix structure; chapter summaries may be removed unless the supervisor identifies a programme-specific rule. | Rewrite Chapter 1 to the 1,400--1,600-word target while checking every retained claim against the frozen evidence. |
| 2026-10-22 | Replaced Chapter 1's nine sections, fifteen subsections, nineteen objectives, and eleven contributions with the planned five-part structure. Preserved all four research questions and externally used labels. | Approximately 1,456 source words, down from the 8,232-word baseline and within target. Static reference and delimiter checks passed. Compilation is pending because MiKTeX reports incomplete first-run setup. | Complete MiKTeX setup, compile and visually check Chapter 1, record its rendered page count, then mark the chapter complete and begin Chapter 3. |
| 2026-10-22 | Completed MiKTeX compilation and the Chapter 1 layout pass. Tightened list spacing and shortened only the dissertation-navigation sentence after the first render showed a two-line spill onto page 5. Regenerated the PDF, table of contents, List of Figures, and List of Tables; checked the final log and visually inspected all four chapter pages. | Chapter 1 is 1,401 words and occupies numbered pages 1--4; Chapter 2 starts on page 5, so the former blank verso is gone and the full PDF falls from 155 to 153 physical pages. No undefined citations/references or LaTeX errors remain, and no Chapter 1 clipping, overflow, or poor page break was found. | Rewrite Chapter 3 to its five-page, 1,700--2,000-word target, preserving one principal architecture diagram and moving the complete requirement inventory out of the main narrative. |
| 2026-10-22 | Rewrote Chapter 3 from 29 headings to the planned four-section argument. Retained the principal architecture diagram, consolidated all FR1--FR29 and NFR1--NFR14 identifiers into nine requirement groups, centralised the dialogue/affect/safety authority boundaries, and reduced ethics and limitations to design-relevant constraints. | Chapter 3 is 1,712 words, down from the 7,889-word baseline, and occupies five content pages (23--27). The full PDF falls from 153 to 137 physical pages. Compilation, cross-references, warning audit, and visual inspection passed; the intentional page 28 verso remains before Chapter 4. The atomic requirement wording is designated for Appendix B. | Rewrite Chapter 4 to its eight-page, 3,000--3,500-word target, retaining only technically significant implementation mechanisms and the four planned visuals. |

## Decisions and open questions

| Date | Decision or question | Status |
|---|---|---|
| 2026-10-22 | Treat the coordinator's 30--40 pages as applying to numbered Chapters 1--6 only. | Accepted based on the quoted guidance. |
| 2026-10-22 | Use 36--37 pages as the working target rather than aiming directly at the 40-page ceiling. | Accepted. |
| 2026-10-22 | Preserve Chapter 5 as the principal evidence chapter and cut descriptive chapters more aggressively. | Accepted. |
| 2026-10-22 | Use Chapter 5 as the authoritative source for all scores, test counts, pilot results, and limitations. | Accepted; frozen checklist added above. |
| 2026-10-22 | The standardised template contains Lists of Figures/Tables and an appendix mechanism, while no accessible rule requires chapter-end summaries. | Retain the lists and appendix structure; summaries may be removed, subject to supervisor confirmation of any unpublished programme-specific rule. |
| 2026-10-22 | Chapter 1 should state the problem and contribution without previewing numerical results, test counts, or detailed implementation. | Accepted and implemented; exact evidence remains in Chapter 5. |

## Current next action

Rewrite Chapter 4 to the planned six-part structure and its eight-page, 3,000--3,500-word target. Retain the emotion pipeline, request sequence, one dialogue-state or affect-policy diagram, and one combined or representative interface figure; remove repository/configuration narration, evaluation results, routine account mechanics, and duplicated protocol or limitation material. Preserve the deterministic dialogue, evidence-extraction, affect-pacing, feedback, security, persistence, and failure-boundary mechanisms needed to understand the contribution.
