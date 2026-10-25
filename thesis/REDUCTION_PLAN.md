# Dissertation Reduction Plan

Last updated: 2026-10-25  
Overall status: Chapters 1--6 complete and verified; appendix reduction and organisation next
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

The baseline PDF contains 161 physical pages. Based on its table of contents, the six numbered chapters occupy approximately 140 pages, including chapter-opening layout and intervening blank pages. At the initial audit, the chapter sources contained approximately 53,155 source words; this count includes some LaTeX and table content and is therefore an approximate tracking measure rather than a polished-prose count. After the Chapter 1--6 rewrites, the current total is approximately 13,483 source words. The current build contains 37 numbered-chapter content pages, meeting the working target.

| Part | Baseline pages | Baseline source words | Target pages | Target words | Status |
|---|---:|---:|---:|---:|---|
| Chapter 1: Introduction | 22 | 8,232 | 4 | 1,400--1,600 | `[x]` |
| Chapter 2: State of the Art | 18 | 6,860 | 6 | 2,300--2,600 | `[x]` |
| Chapter 3: Proposed System Architecture | 22 | 7,889 | 5 | 1,700--2,000 | `[x]` |
| Chapter 4: Implementation | 46 | 16,934 | 8 | 3,000--3,500 | `[x]` |
| Chapter 5: Evaluation and Results | 22 | 9,289 | 10--11 | 4,000--4,500 | `[x]` |
| Chapter 6: Conclusions and Future Work | 10 | 3,951 | 3 | 1,000--1,300 | `[x]` |
| **Total main content** | **about 140** | **53,155** | **36--37** | **13,400--15,500** | `[x]` |

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

- [x] Merge the many short subsections into the five themes above.
- [x] Retain only literature that directly motivates a research question or design decision.
- [x] Compress textbook-style explanations of BERT, wav2vec, emotion taxonomies, and calibration.
- [x] Remove or move the secondary-dataset catalogue and comparison table.
- [x] Reduce legal, privacy, and safety literature to the constraints relevant to the design.
- [x] Remove descriptions of AffectLab implementation that belong in Chapters 3 and 4.
- [x] Replace the large synthesis table with concise prose unless it adds unique comparative value.
- [x] End with a precise integration-and-evaluation research gap.
- [x] Keep the chapter summary to one short paragraph or remove it if permitted.

Completion condition: every retained source contributes directly to the research gap, method, or design rationale.

Current result: the chapter now has the planned five-section structure and 2,313 words by `texcount`, down from the 6,860-word baseline. It removes the dataset catalogue, synthesis table, literature-gap figure, textbook-style model explanations, and implementation-specific narration while preserving the literature needed for the research questions and design boundaries. The chapter occupies numbered pages 5--10, and Chapter 3 begins on page 11. A clean `latexmk` build contains no undefined citations or references, LaTeX errors, or Chapter 2 overfull boxes; visual inspection of all six rendered pages found no clipping or poor page breaks. The full PDF is 83 physical pages.

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

Current result: the chapter has the planned four sections, one architecture figure, and one table containing nine grouped requirement families. It contains 1,712 words by `texcount`, down from the 7,889-word baseline, and occupies numbered pages 11--15 in the current build. Chapter 4 begins on page 17 after the standard template's intentional blank verso. A clean `latexmk` build contains no undefined citations or references, LaTeX errors, or Chapter 3 overfull boxes; visual inspection of all five content pages found the diagram and table legible with no clipping or poor page breaks. The full 43-item requirement wording is identified for Appendix B but has not yet been inserted.

## Chapter 4: Implementation -- target 8 pages

Planned structure:

1. Technology and application overview: approximately 0.5 page.
2. Emotion-recognition pipeline: approximately 1.5 pages.
3. Backend and request processing: approximately 1.5 pages.
4. Role-play and affect-adaptation engine: approximately 2 pages.
5. Feedback and frontend workflow: approximately 1.5 pages.
6. Security, persistence, and deployment: approximately 1 page.

Tasks:

- [x] Replace the technology inventory with a short stack overview.
- [x] Remove repository-structure and configuration-file narration.
- [x] Keep implementation choices that distinguish the contextual text, speech, fusion, calibration, and inference pipeline.
- [x] Remove evaluation-protocol repetition; the definitive protocol belongs in Chapter 5.
- [x] Condense domain models and API schemas to their architectural role.
- [x] Remove routine authentication and account-management mechanics.
- [x] Keep one concise request-processing description and its sequence diagram.
- [x] Preserve the deterministic dialogue, evidence-extraction, and affect-pacing mechanisms.
- [x] Condense feedback, replay, branching, and action cards into one section.
- [x] Replace multiple interface screenshots with one combined figure or one representative screen.
- [x] Reduce optional research-support implementation to one paragraph.
- [x] Reduce security, privacy, and deployment controls to the decisions relevant to the dissertation contribution.
- [x] Remove the Implementation Verification section; evaluation results belong in Chapter 5.
- [x] Remove the repetitive chapter summary.

Main-text visual budget:

- [x] Emotion pipeline.
- [x] Request sequence.
- [x] Dialogue-state or affect-policy diagram; retained the affect-policy diagram.
- [x] One combined or representative interface figure.

Candidates for appendix or repository documentation:

- [x] Complete repository and configuration description retained only in repository documentation.
- [x] Detailed API/domain-model information retained only in repository documentation.
- [x] Research-data lifecycle diagram removed from the main chapter; the lifecycle boundary remains in concise prose.
- [x] Deployment topology removed from the main chapter; operational detail remains in repository documentation.
- [x] Additional screenshots excluded rather than moved automatically.
- [x] Detailed test architecture and provenance procedures removed from Chapter 4; evidence remains in Chapter 5 and repository artefacts.

Completion condition: the chapter explains the technically original implementation choices, not every implemented feature.

Current result: the chapter now follows the planned six-section structure and contains 3,016 words by `texcount`, down from the 16,934-word baseline. It retains four visuals: the emotion pipeline, request sequence, affect-pacing policy, and one representative role-play screen. In the current build, the chapter occupies numbered pages 17--24 and Chapter 5 begins on page 25. A clean `latexmk` build contains no undefined citations or references, LaTeX errors, or Chapter 4 overfull boxes; visual inspection of all eight rendered pages found no clipping or poor page breaks.

## Chapter 5: Evaluation and Results -- target 10--11 pages

Planned structure:

1. Evaluation methodology: approximately 2 pages.
2. Contextual-text results: approximately 1.5 pages.
3. Speech, fusion, and calibration results: approximately 3 pages.
4. Application verification: approximately 1.5--2 pages.
5. Pilot results: approximately 1 page.
6. Threats to validity: approximately 1 page.

Tasks:

- [x] Retain the speaker-independent task, folds, metrics, and dialogue-level statistical comparison.
- [x] Retain the primary four-class contextual-text experiment.
- [x] Retain the audio, equal-weight fusion, and calibration trade-off results.
- [x] Select only the tables and figures required to support the principal claims.
- [~] Move the exploratory six-class experiment to an appendix. Extracted to `appendix_c_supplementary_model_results.tex`; insertion is deferred until Appendix B fixes the final ordering.
- [~] Move full per-class and per-fold tables to an appendix. Extracted to the prepared Appendix C source; insertion is deferred until the appendix phase.
- [x] Reduce the operational packaging analysis to one short paragraph or move it.
- [x] Condense the comparison with published IEMOCAP results.
- [x] Replace detailed authored-case and test-suite tables with one aggregate verification table.
- [~] Move the complete requirement-to-test traceability matrix to an appendix. Extracted to `appendix_d_verification_details.tex`; insertion is deferred until the appendix phase.
- [x] Report exact test counts once.
- [x] Keep the pilot results and state their scope limitation once, immediately beside them.
- [x] Consolidate model, construct, external, pilot, and application limitations in Threats to Validity.
- [x] Remove the separate Answer to RQ1--RQ4 subsections; final answers belong in Chapter 6.
- [x] Remove or reduce the chapter summary to a transition paragraph.

Completion condition: every principal conclusion is supported by visible evidence, while secondary and audit-level evidence remains available outside the main narrative.

Current result: the chapter now follows the planned six-part structure and contains 4,027 words by `texcount`, down from the 9,289-word baseline. It retains the principal contextual-text, equal-fusion, calibration, aggregate application-verification, and pilot tables plus one combined model figure. The chapter occupies numbered pages 25--35; Chapter 6 begins on page 37 after the template's intentional blank verso. The clean `latexmk` build contains no undefined citations or references, LaTeX errors, or Chapter 5 overfull boxes. Visual inspection of all eleven rendered pages found no clipping, illegible material, or poor float/page breaks. The full PDF is 67 physical pages. Secondary model tables and detailed application-verification evidence have been extracted to prepared Appendix C and D sources without inserting them ahead of the still-pending Appendix B.

## Chapter 6: Conclusions and Future Work -- target 3 pages

Planned structure:

1. Direct answers to RQ1--RQ4: approximately 1.5 pages.
2. Contributions and limitations: approximately 0.75 page.
3. Prioritised future work: approximately 0.5 page.
4. Final conclusion: approximately 0.25 page.

Tasks:

- [x] Delete Chapter Overview.
- [x] Delete the long Summary of the Dissertation.
- [x] Answer the four research questions in compact paragraphs or one table.
- [x] Merge the three contribution subsections.
- [x] Summarise only the limitations that materially qualify the final conclusions.
- [x] Keep the future-work roadmap but remove the six subsections that restate it.
- [x] Avoid repeating detailed scores, test counts, and implementation descriptions.
- [x] End with one restrained conclusion paragraph.

Completion condition: the chapter answers the research questions and states what the work establishes without summarising the dissertation chapter by chapter.

Current result: the chapter now follows the planned four-part structure and contains 1,014 words by `texcount`, down from the 3,951-word baseline. It answers RQ1--RQ4 directly, merges the contributions and material limitations, replaces the table-plus-six-subsection future-work roadmap with three prioritised paragraphs, and ends with one bounded conclusion. The chapter occupies numbered pages 37--39, bringing Chapters 1--6 to the 37-page working target. The clean `latexmk` build contains no undefined citations or references, LaTeX errors, or overfull boxes; visual inspection of all three rendered pages found no clipping or poor page breaks. The full PDF is 59 physical pages.

## Appendices plan

Appendices do not count toward the coordinator's recommended 30--40 content pages, but they should remain concise and useful.

| Appendix | Proposed contents | Status |
|---|---|---|
| A | Generative AI declaration, reduced to the required disclosure | `[ ]` |
| B | Complete functional and non-functional requirements | `[~]` Identified from the former Chapter 3 inventory; insertion deferred to the appendix phase |
| C | Supplementary model results: six-class, per-class, and per-fold tables | `[~]` Selective source prepared in `appendix_c_supplementary_model_results.tex`; insertion deferred until Appendix B is assembled |
| D | Application-verification details and requirement traceability | `[~]` Selective source prepared in `appendix_d_verification_details.tex`; insertion deferred until Appendix B is assembled |
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
- [x] Rewrite Chapter 4.
- [x] Condense Chapter 2.
- [x] Refine Chapter 5 and extract appendix material.
- [x] Rewrite Chapter 6.
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
| 2026-10-22 | Rewrote Chapter 4 from 12 sections and 45 subsections to the planned six-section implementation argument. Removed the technology inventory, repository/configuration tour, routine account mechanics, detailed research lifecycle, separate verification section, chapter summary, six surplus diagrams/screenshots, and repeated evaluation material. | Chapter 4 is 3,016 words, down from the 16,934-word baseline, and occupies numbered pages 29--36. It retains the four planned visuals and preserves compatibility labels still used by Chapter 5. The clean build, cross-reference audit, warning audit, and visual inspection passed; Chapter 5 starts on page 37, and the full PDF falls from 137 to 97 physical pages. | Condense Chapter 2 to its six-page, 2,300--2,600-word target, retaining only literature that directly supports the research gap, method, or design rationale. |
| 2026-10-22 | Rewrote Chapter 2 from 14 sections and numerous short subsections to the planned five-theme argument. Removed the secondary-dataset catalogue, two comparison tables, the literature-gap figure, the standalone chapter summary, implementation detail, and extended textbook explanations; retained 33 directly relevant citation keys. | Chapter 2 is 2,313 words, down from the 6,860-word baseline, and occupies numbered pages 5--10. The full PDF falls from 97 to 83 physical pages, and Chapter 3 now begins on page 11. The clean build, citation and cross-reference audit, Chapter 2 warning audit, and visual inspection of all six pages passed. | Refine Chapter 5 to its 10--11-page, 4,000--4,500-word target and extract only genuinely useful supplementary evidence for Appendices C and D. |
| 2026-10-25 | Rewrote Chapter 5 from eight sections and numerous evidence/audit subsections to the planned six-part evaluation argument. Retained the speaker-independent protocol, principal RQ1--RQ4 evidence, calibration distinction, aggregate application verification, bounded pilot interpretation, and consolidated threats to validity. Extracted selected six-class, per-class, per-fold, policy, traceability, and performance detail into prepared Appendix C and D source files. | Chapter 5 is 4,027 words, down from the 9,289-word baseline, and occupies numbered pages 25--35. It retains five necessary tables and one combined model figure. The full PDF is 67 physical pages. The clean build, citation/reference audit, warning audit, and visual inspection of all eleven pages passed; Appendix C/D insertion remains deferred so Appendix B can establish the intended ordering. | Rewrite Chapter 6 to its three-page, 1,000--1,300-word target, answering RQ1--RQ4 directly without repeating Chapter 5's evidence detail. |
| 2026-10-25 | Rewrote Chapter 6 from seven sections, thirteen subsections, and a large future-work table to the planned four-part conclusion. Removed the chapter overview and chapter-by-chapter summary, answered RQ1--RQ4 directly, merged contributions with material limitations, and reduced future work to immediate, next, and longer-term priorities. | Chapter 6 is 1,014 words, down from the 3,951-word baseline, and occupies numbered pages 37--39. Chapters 1--6 now total 37 content pages and approximately 13,483 words. The full PDF is 59 physical pages. The clean build, reference/error/overfull-box audit, and visual inspection of all three pages passed. | Reduce the generative-AI declaration to the required disclosure, assemble selective Appendices B--D in order, and omit Appendix E unless a concrete need emerges. |

## Decisions and open questions

| Date | Decision or question | Status |
|---|---|---|
| 2026-10-22 | Treat the coordinator's 30--40 pages as applying to numbered Chapters 1--6 only. | Accepted based on the quoted guidance. |
| 2026-10-22 | Use 36--37 pages as the working target rather than aiming directly at the 40-page ceiling. | Accepted. |
| 2026-10-22 | Preserve Chapter 5 as the principal evidence chapter and cut descriptive chapters more aggressively. | Accepted. |
| 2026-10-22 | Use Chapter 5 as the authoritative source for all scores, test counts, pilot results, and limitations. | Accepted; frozen checklist added above. |
| 2026-10-22 | The standardised template contains Lists of Figures/Tables and an appendix mechanism, while no accessible rule requires chapter-end summaries. | Retain the lists and appendix structure; summaries may be removed, subject to supervisor confirmation of any unpublished programme-specific rule. |
| 2026-10-22 | Chapter 1 should state the problem and contribution without previewing numerical results, test counts, or detailed implementation. | Accepted and implemented; exact evidence remains in Chapter 5. |
| 2026-10-22 | Chapter 4 should explain only the technically significant mechanisms and preserve compatibility labels until Chapter 5 is condensed. | Accepted and implemented; detailed software, deployment, research-workflow, and verification material remains in repository documentation or Chapter 5 rather than the main implementation narrative. |
| 2026-10-22 | Chapter 2's dataset catalogue, synthesis table, and literature-gap figure should be deleted rather than moved because concise prose preserves their argument and the removed presentation adds no unique supporting evidence. | Accepted and implemented. |
| 2026-10-25 | Chapter 5 should retain five evidence tables and one combined model figure; confusion matrices, reliability curves, exhaustive case tables, commands, environment details, and node IDs are not required in the main narrative. | Accepted and implemented. Selective reproducibility evidence is preserved in prepared Appendix C/D sources; routine operational detail remains in repository artefacts. |
| 2026-10-25 | Prepared Appendix C and D sources should not yet be inserted because Appendix B has not been assembled and inserting them now would assign the wrong appendix letters. | Accepted. The files are ready for the later appendix phase, when A--D will be ordered and compiled together. |
| 2026-10-25 | Chapter 6 should answer each research question qualitatively and refer detailed values back to Chapter 5 rather than reproducing score and test-count inventories. | Accepted and implemented. The conclusion preserves the decisive findings and qualifications without duplicating Chapter 5's evidence tables. |

## Current next action

Begin the appendix phase: reduce Appendix A to the required generative-AI disclosure, assemble the complete atomic requirement inventory as Appendix B, then insert and verify the prepared selective Appendix C and D sources in that order. Add Appendix E only if a specific figure is required for reproducibility or supporting evidence.
