# Dissertation Reduction Plan

Last updated: 2026-10-22  
Overall status: Planning complete; content editing not started  
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

The baseline PDF contains 161 physical pages. Based on its table of contents, the six numbered chapters occupy approximately 140 pages, including chapter-opening layout and intervening blank pages. The current chapter sources contain approximately 53,155 source words; this count includes some LaTeX and table content and is therefore an approximate tracking measure rather than a polished-prose count.

| Part | Baseline pages | Baseline source words | Target pages | Target words | Status |
|---|---:|---:|---:|---:|---|
| Chapter 1: Introduction | 22 | 8,232 | 4 | 1,400--1,600 | `[ ]` |
| Chapter 2: State of the Art | 18 | 6,860 | 6 | 2,300--2,600 | `[ ]` |
| Chapter 3: Proposed System Architecture | 22 | 7,889 | 5 | 1,700--2,000 | `[ ]` |
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

- [ ] Extract the final numerical claims from Chapter 5 into a short working checklist.
- [ ] Record which tables and figures directly support RQ1--RQ4.
- [ ] Mark Chapter 5 as the authoritative source for scores, test counts, pilot results, and limitations.
- [ ] Identify any results in the abstract that no longer match Chapter 5.
- [ ] Confirm whether the university requires chapter summaries, lists of figures/tables, or a particular appendix structure.

Completion condition: all essential claims and their supporting evidence are known before duplicated passages are removed elsewhere.

## Chapter 1: Introduction -- target 4 pages

Planned structure:

1. Context and problem: approximately 1 page.
2. Aim and objectives: approximately 0.5 page.
3. Research questions: approximately 0.5 page.
4. Proposed approach and contributions: approximately 1.5 pages.
5. Scope and dissertation structure: approximately 0.5 page.

Tasks:

- [ ] Rewrite Context and Motivation as a short problem-led opening.
- [ ] Remove literature discussion of role-play, IMBUE, IEMOCAP, emotion theory, and calibration; retain it only in Chapter 2.
- [ ] Merge Aim and Objectives into a compact section.
- [ ] Preserve the four research questions without extended commentary.
- [ ] Replace the five Proposed Approach subsections with a compact overview.
- [ ] Reduce Contributions to four or five concrete contributions.
- [ ] Replace the ten Scope and Limitations subsections with one short scope section.
- [ ] Remove numerical results, test counts, and detailed implementation descriptions.
- [ ] Reduce Dissertation Structure to one paragraph.
- [ ] Verify that no claim is stronger than the evidence later presented in Chapter 5.

Completion condition: a reader can understand the problem, questions, approach, contribution, and scope without receiving a preview of every later chapter.

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

- [ ] Keep one principal architecture diagram.
- [ ] Explain the separation between inference, dialogue control, generation, feedback, and safety once.
- [ ] Replace 29 functional and 14 non-functional requirement descriptions with 8--10 grouped requirements.
- [ ] Move the complete requirement list to an appendix.
- [ ] Merge scope, assumptions, and boundaries into a concise passage or table.
- [ ] Reduce the ethics section to the safeguards that materially shaped the architecture.
- [ ] Remove the detailed Limitations of the Proposed System subsections; consolidate limitations in Chapter 5.
- [ ] Remove repeated pilot, IEMOCAP, generative-AI, and deployment caveats.
- [ ] Remove the repetitive chapter summary.

Completion condition: the chapter explains why the architecture is structured as it is without duplicating implementation or evaluation material.

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
| B | Complete functional and non-functional requirements | `[ ]` |
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

- [ ] Phase 0: freeze the evidence and principal claims from Chapter 5.
- [ ] Rewrite Chapter 1.
- [ ] Rewrite Chapter 3.
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

## Decisions and open questions

| Date | Decision or question | Status |
|---|---|---|
| 2026-10-22 | Treat the coordinator's 30--40 pages as applying to numbered Chapters 1--6 only. | Accepted based on the quoted guidance. |
| 2026-10-22 | Use 36--37 pages as the working target rather than aiming directly at the 40-page ceiling. | Accepted. |
| 2026-10-22 | Preserve Chapter 5 as the principal evidence chapter and cut descriptive chapters more aggressively. | Accepted. |
| 2026-10-22 | Confirm whether chapter summaries and Lists of Figures/Tables are mandatory under faculty formatting rules. | Open. |

## Current next action

Create the Phase 0 evidence checklist from Chapter 5: principal numerical findings, supporting tables/figures, application-verification claims, pilot results, and the limitations that must survive every later reduction.
