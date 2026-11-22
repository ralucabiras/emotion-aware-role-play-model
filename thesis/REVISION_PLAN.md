# Dissertation Revision Plan

Created: 2026-11-22  
Status: Revision in progress; Notes 1, 2, 3, 4, 6, and 7 completed and checked. Note 5 partially addressed; final length review remains open.

This tracker covers the author's 20 reading notes and the changes proposed in the accompanying review. Use it to record what remains to be revised and checked.

## Scope and tracking

- Work only on the issues listed below. This is a separate tracker; leave `REDUCTION_PLAN.md` unchanged.
- **Leave the pilot alone.** Do not investigate, reclassify, remove, rewrite, or recalculate the pilot. Preserve Section 5.5, its table, and pilot-related claims, qualifications, and references elsewhere, including the abstract and conclusions. Note 13 is recorded as excluded from this revision.
- Preserve numerical findings and methodological meaning when simplifying other material.
- `[ ]` means pending; `[x]` means completed and checked. Mark an action complete only after checking its result. Record completed work in the revision log at the end.
- Page numbers below identify the reviewed PDF. Use section names and source files to find passages after pagination changes.

## Revision checklist

### Note 1 Abstract

Location: `main_file_template_bachelor_masters_english.tex`, Abstract.

- [x] Rewrite the surrounding abstract to explain the problem, what AffectLab enables, what was implemented, how it was evaluated, and the main findings.
- [x] Retain only the most informative technical results; remove the inventory of test counts, precise local latency, and unfinished provenance detail.
- [x] Keep the existing pilot passage unchanged.

Complete when the abstract gives a readable account of the work rather than a compressed technical report, while preserving the pilot text.

### Note 2 Empty pages

Location: main document class, chapter openings, and explicit page-clearing commands.

Confirmed bodyless pages in the reviewed PDF: VIII, X, XII, 16, 26, 38, 42, 48, and 60. These came from right-hand chapter openings in the `book` class and explicit `\cleardoublepage` commands; several retained running headers.

- [x] Check the applicable thesis layout requirements before changing chapter-opening behaviour.
- [x] Where permitted, remove unnecessary blank versos by addressing both class options and explicit page-clearing commands.
- [x] Inspect the rebuilt PDF for remaining accidental blank pages and headers on retained blank pages.

Layout check (2026-11-22): Section 5 of both the [2025–2026 English guide](https://drive.google.com/file/d/1PijhYd6nSlfeQuIFSW16uulRf3joTObi/view) and the [2026–2027 English guide](https://drive.google.com/file/d/1w9IxWH3NiI_ndve3EGLT7xehv2HlSuWk/view), linked from the [faculty's master-completion page](https://info.uvt.ro/finalizarea-studiilor-universitare-master/), requires chapters to begin on a new page; neither specifies right-hand openings or blank versos. Retained new-page openings, existing margins, typography, and two-sided running headers. Selected `openany`, replaced explicit double-page clears with `\clearpage`, and made the class's internal double-page clears use `\clearpage` as well, including the transition to the main matter. Removed the obsolete empty-verso header suppression.

Checked result: 67 physical pages, down from 76. All nine bodyless pages are removed. Text extraction across all 67 pages and visual inspection of rendered page overviews found no remaining empty or header-only pages. Chapters 1–6 contain 38 pages of content, unchanged; the reduction is entirely pagination. No blank pages were retained.

Complete when blank pages are either removed or retained for a documented formatting requirement.

### Note 3 Context and Problem

Location: `cap1.tex`, Section 1.1.

- [x] Lead with the human difficulty of anticipating confrontation, feeling anxious, avoiding a conversation, or struggling to find words.
- [x] Explain the value of private, repeatable rehearsal before introducing model and architecture terminology.
- [x] Keep anxiety as motivation without suggesting that the application diagnoses or treats it.

Complete when the opening makes the need for the application understandable before presenting its technical challenges.

### Note 4 Equations

Locations: `cap2.tex`, `cap4.tex`, and `cap5.tex`; reviewed pages 8, 19, and 29.

- [x] Replace the displayed causal-context notation in Chapter 2 with a clear explanation of using the current and preceding turns, without future turns.
- [x] Remove the duplicate displayed fusion equation from the literature discussion.
- [x] Retain one fusion equation in the implementation chapter and define its terms plainly.
- [x] Explain temperature scaling in prose or inline notation instead of a separate displayed equation, preserving how validation data determine the temperature.
- [x] Remove obsolete equation references and check the surrounding explanations.

Complete when each retained formula adds necessary precision and no formula repeats another explanation without purpose.

### Note 5 Overall length

Reviewed baseline: 76 physical pages, including nine bodyless pages. Chapters 1–6 occupy 42 numbered pages, of which 38 contain content; page 25 contains only a short continuation.

- [ ] Reduce length through the removals, consolidation, and layout changes in this tracker, without changing pilot material.
- [ ] Remove avoidable sparse continuation pages and excessive float whitespace.
- [x] Record the resulting physical page count and numbered-chapter content count after rebuilding.

Working direction: approximately 30–32 chapter-content pages and roughly 50–55 physical pages overall, if achievable while preserving the pilot, required formatting, and readable figures. These are editorial targets, not reasons to shrink text or crowd content.

Checked progress (2026-11-22): rebuilt the PDF after removing one redundant 64-word overview paragraph from Section 4.1. Its points about deterministic control, optional models, and fallback behaviour remain explained in the preceding overview and the relevant implementation sections. This eliminates Chapter 4's short final continuation, formerly numbered page 24 (the corresponding sparse continuation in the reviewed baseline was page 25), without changing pilot material, typography, margins, or figure sizes.

| Part | Pages at the Note 5 check (before Note 7) |
| --- | --- |
| Front matter | 9 |
| Chapters 1–6 | 37 content pages: 4 + 6 + 5 + 8 + 11 + 3 |
| Bibliography | 4 |
| Appendices A–D | 16: 1 + 6 + 5 + 4 |
| **Physical total** | **66** |

Chapters 1–6 now occupy numbered pages 1–37, with no bodyless pages. The physical total is down from the reviewed 76-page baseline by ten pages: nine blank pages removed under Note 2 and one continuation page removed here. Visually checked all eight rebuilt Chapter 4 pages (numbered 16–23); the chapter ends on a full page, and its floats leave no excessive whitespace. The existing diagram-label and screenshot-readability issues remain assigned to Notes 7 and 9.

Remaining work: the current build is still 5–7 chapter-content pages and 11–16 physical pages above the working direction. Appendix C still occupies five pages, including a sparse packaging-diagnostic page (numbered 53); reduce it under Notes 15 and 16. Appendix D still occupies four pages and ends with an isolated latency table (numbered 57); consolidate it under Note 17. Main-text consolidation under Notes 19 and 20, together with the shorter passages in Notes 6, 10, and 12, remains the route to further chapter reduction. Recheck the budget after the figure and screenshot revisions under Notes 7, 9, 11, and 18, since readable replacements may need more space. Leave the first two actions open until those revisions and the final pagination review are complete; refresh the recorded counts at that point.

### Note 6 Opening of Section 3.2

Location: `cap3.tex`, Grouped System Requirements.

- [x] Replace the opening about the original specification and its consolidation with an explanation of the capabilities users need.
- [x] Introduce the requirement groups and identifiers after their purpose is clear.
- [x] Remove editorial justification such as “This grouping is sufficient for the design argument.”

Complete when the opening explains system requirements rather than the history of editing the dissertation.

### Note 7 Technical figures

Locations: `figures/system_architecture.tex`, `emotion_pipeline.tex`, `request_sequence.tex`, and `affect_policy.tex`.

- [x] Redesign Figure 3.1 to separate components and avoid crossing or overlapping connections.
- [x] Redesign Figure 4.1 with fewer crowded boxes, shorter labels, and clearly separated evaluation and packaging paths.
- [x] Simplify Figure 4.2 so message labels are readable at normal PDF viewing size.
- [x] Redesign Figure 4.3 to separate the lower decision branches and their labels.
- [x] Use consistent typography, spacing, and visual conventions; revise captions and surrounding discussion to match.

Checked result (2026-11-22): rebuilt all four TikZ diagrams with shared styles in `figures/technical_diagram_styles.tex`, native 10-point sans-serif labels, and no resizing. Figure 3.1 uses a central control path with separate evidence, wording, storage, and feedback connections. Figure 4.1 uses seven boxes in distinct evaluation and application-packaging paths; its dashed transfer and caption identify operational settings fitted from pooled validation-role predictions. Figure 4.2 reduces seven lanes to browser, backend, and repository, groups internal backend steps, and rejoins the safety and ordinary branches before commit and reply. Figure 4.3 uses ordered checks with separate terminal actions and two lower emotion groups; explicit preference precedes the automatic-enabled and estimate checks, matching the implementation. Updated captions, concise List of Figures entries, and the directly related discussion.

Rebuilt successfully and visually checked all 14 Chapter 3 and 4 pages, including the diagrams on numbered pages 12, 17, 20, and 22 at 95 dpi. No overlapping boxes, arrows, or labels, clipping, isolated figure page, or one-word continuation remains. No LaTeX errors, undefined citations/references, or overfull boxes; all 35 bibliography entries remain cited. Source hashes and exact text comparisons confirm that all pilot material, numerical findings, other chapter text, other thesis sources, and `REDUCTION_PLAN.md` are unchanged. The PDF now has 67 physical pages and 38 chapter-content pages (4 + 6 + 5 + 9 + 11 + 3): one additional Chapter 4 page compared with the Note 5/6 build. Note 5 remains open for consolidation and the final page-budget review; the screenshot and model-results revisions remain assigned to Notes 9 and 11.

Complete when boxes, arrows, and text do not overlap and every retained label is readable without substantial zooming. Enlarging the current diagrams alone is insufficient.

### Note 8 Pending model file hashes

Location: `cap4.tex`, Emotion-Recognition Pipeline, paragraph about the private inference package.

The sentence refers to missing digital fingerprints for the final model files, rather than a reported model failure.

- [ ] Check whether a completed model-file manifest is available.
- [ ] If the relevant files are available, capture and record their hashes; otherwise retain a precise statement of the remaining provenance limitation.
- [ ] Replace vague “audit cut-off” wording with a factual account of what was recorded.
- [ ] Keep the detailed provenance explanation in one appropriate location, coordinated with Note 16.

Complete when the text accurately describes the available model-file provenance and contains no vague unfinished-task language.

### Note 9 Application screenshots

Location: `cap4.tex`, Feedback and Frontend Workflow; `figures/app-dashboard.png`, `app-roleplay.png`, and `app-feedback.png`.

- [ ] Expand the interface presentation into a short walkthrough of entering or resuming practice, conducting a rehearsal, and reviewing feedback.
- [ ] Use the existing screenshots where suitable, with labelled panels and a short explanation of each view.
- [ ] Remove the restrictive screenshot height that makes the current interface text too small.
- [ ] Choose one sufficiently large composite or two figures according to readability; avoid miniature panels.

Complete when the figures and accompanying text explain the actual user journey and visible features.

### Note 10 Last sentence of Section 5.1

Location: `cap5.tex`, Evaluation Methodology and Measures and Statistical Comparison.

- [ ] Remove the generic deployment-readiness sentence immediately before Section 5.1.1, or consolidate its meaning into the existing application-validity discussion.
- [ ] Simplify the final sentence of Section 5.1.3 about per-class metrics: distinguish descriptive class scores from the specified comparisons with paired bootstrap intervals.

Complete when the methodology ends with relevant methodological information and avoids repeating later qualifications. Preserve all pilot-related wording.

### Note 11 Alignment of Figure 5.1

Location: `figures/model_results.tex`.

- [ ] Rebuild the panels in one aligned plot layout rather than independently aligned boxes with different label extents.
- [ ] Align plot areas and panel titles; use consistent typography and appropriate common macro-F1 limits.
- [ ] Check axis labels, point labels, margins, and the caption at the final printed size.

Complete when panels (a) and (b) align visually and neither looks displaced above the other.

### Note 12 Thirteen skipped tests

Location: `cap5.tex`, Section 5.4.2, and its aggregate verification table.

- [ ] State directly that 245 tests passed and 13 MongoDB integration tests were not run because the required test database connection was not configured.
- [ ] Distinguish those unexecuted tests from the two separate database-backed full-stack journeys; do not imply that the journeys replace all 13 tests.
- [ ] Remove repeated explanations of this distinction from other verification passages.

Suggested wording: “The default backend suite passed 245 tests. Thirteen additional MongoDB integration tests were not run because the required test database connection was not configured. Two separate full-stack journeys verified selected database-backed workflows.”

Complete when the counts and scope are clear and skipped tests are neither presented as passes nor confused with failures. Rerunning tests is not part of this wording task.

### Note 13 Last two sentences of Section 5.5

Location: `cap5.tex`, Supplementary Pilot Results.

**Excluded by the author's instruction to leave the pilot alone.** Keep these sentences and the rest of the pilot material unchanged. No action is scheduled.

### Note 14 Bibliography usage

Locations: `myBib.bib`, citations throughout the dissertation, and the generated bibliography.

- [x] Verify the reviewed version: all 35 bibliography entries are cited, with no undefined citation keys or unused entries.
- [ ] After the scoped revisions, repeat the citation check and remove any newly unused entries rather than adding unnecessary citations to retain them.

Complete when the final bibliography contains the sources actually cited in the revised dissertation.

### Note 15 Appendix C

Location: `appendix_c_supplementary_model_results.tex`.

- [ ] Reduce Appendix C to approximately one or two readable pages containing only useful reproducibility settings and selected four-class supporting results.
- [ ] Remove the exploratory six-class tables from the dissertation and retain their detail in repository documentation.
- [ ] Move long identifiers, extensive packaging diagnostics, and routine archive detail to the existing evidence package.
- [ ] Shorten or remove references elsewhere to material removed from the appendix, without changing pilot material.
- [ ] Replace selected numeric tables with a visual only where it improves interpretation, following Note 18.

Complete when every remaining appendix item supports the main argument and the appendix is readable without dense inventories.

### Note 16 Second paragraph of C.1

Location: `appendix_c_supplementary_model_results.tex`, Reproduction Provenance.

- [ ] Coordinate with Note 8 to describe restricted access and model-file provenance accurately.
- [ ] Replace the instruction to run a supplied script with a factual description of the available records and any remaining limitation.
- [ ] Remove duplicated provenance explanations while retaining an honest account of completeness.

Complete when the paragraph reads as a finished account rather than an internal review instruction.

### Note 17 Appendix D

Location: `appendix_d_verification_details.tex`, with possible consolidation into Appendix B.

- [ ] Remove repeated test totals, qualifications, case inventories, and individual latency rows already adequately covered in Chapter 5 or repository evidence.
- [ ] Preserve a compact requirement-to-evidence mapping, preferably alongside Appendix B, if it contributes useful traceability.
- [ ] Remove Appendix D as a separate appendix if its remaining useful material is consolidated elsewhere.
- [ ] Update affected references and remove the isolated final latency-table page.

Complete when verification is explained once in Chapter 5 and supplementary traceability is concise and readable. Preserve pilot-related material wherever it appears.

### Note 18 Visuals instead of excessive tables

Locations: model-result presentations in Chapter 5 and Appendix C; interface presentation in Chapter 4.

- [ ] Assess a per-class F1 heatmap as a replacement for repeated precision, recall, and F1 tables.
- [ ] Assess a session-level point or line plot as a replacement for the wide fold-results table.
- [ ] Use the screenshot walkthrough from Note 9 to replace some interface-description prose.
- [ ] Retain only replacements that reveal a meaningful pattern; keep small exact-value tables where they remain clearer.

Complete when visuals replace less useful material instead of simply increasing the figure count. Pilot tables and results are excluded.

### Note 19 Retain material only for a strong contribution

Locations: all material being revised under this tracker, excluding the pilot.

- [ ] Review each candidate paragraph, table, and figure: would removing it make the research question, method, original implementation, evidence, or interpretation materially harder to understand?
- [ ] Keep essential material; shorten supporting detail; remove duplication and content that supports no central claim.
- [ ] Use repository documentation for routine implementation and exhaustive records rather than automatically moving them into appendices.

Complete when every retained item has a clear role in explaining or defending the dissertation's contribution.

### Note 20 Repetition and duplicate text

Locations: Chapters 1–6 and appendices, excluding all pilot-related passages.

- [ ] Consolidate repeated explanations of uncertain emotion predictions, deterministic control, fallback behaviour, transient audio, accessibility scope, and deployment boundaries.
- [ ] Give each topic one full explanation in its appropriate location; use brief references elsewhere where needed.
- [ ] Remove prose that merely repeats every value already shown in a table or figure.
- [ ] Reconcile Chapter 1's five contributions with Chapter 6's three contribution groups using a consistent account of the work, while preserving pilot-related wording.

Complete when repetition is limited to necessary orientation and final conclusions, rather than repeated full explanations.

## Order of work

1. Select removals and consolidation under Notes 15, 17, 19, and 20; identify the equation reductions in Note 4.
2. Rewrite the motivation, requirements opening, and flagged evaluation wording under Notes 3, 6, 10, and 12.
3. Coordinate the model-provenance wording under Notes 8 and 16.
4. Rebuild figures and the application walkthrough under Notes 7, 9, 11, and 18.
5. Rewrite the abstract under Note 1 once the surrounding presentation is settled, preserving its pilot passage.
6. Resolve pagination and review the page budget under Notes 2 and 5.
7. Recheck citations under Note 14, affected references and captions, numerical consistency, and the rendered pages changed by this work. Confirm that pilot text, results, and interpretation remain unchanged; automatic numbering and pagination may move.

## Revision log

| Date | Notes addressed | Changes made | Verification and remaining work |
| --- | --- | --- | --- |
| 2026-11-22 | Planning only | Created this tracker from the author's 20 notes; excluded pilot work. | No dissertation edits made. Bibliography verification from the review is recorded under Note 14. |
| 2026-11-22 | Note 1: Abstract | Rewrote the abstract around the problem, user workflow, implementation, evaluation, and main findings. Retained the context and fusion macro-F1 results and explained the calibration trade-off in prose; removed test-count inventories, precise local latency, and unfinished model-hash detail. Preserved the three pilot sentences word for word. | Rebuilt the 76-page PDF with no LaTeX errors, undefined citations/references, or overfull boxes. Visually checked that the abstract and keywords fit on one readable page. Verified the retained results against Chapter 5 and confirmed that all source outside the abstract, all other thesis sources, and `REDUCTION_PLAN.md` are unchanged. Remaining notes are pending. |
| 2026-11-22 | Note 2: Empty pages | Checked Section 5 of the faculty's archived 2025–2026 and current 2026–2027 English guides: new-page chapter openings are specified, with no right-hand-opening requirement. Enabled `openany`, replaced explicit double-page clears, made internal class transitions use single-page clears, and removed obsolete blank-verso header suppression. | Rebuilt the PDF successfully: 67 physical pages instead of 76, with all nine bodyless pages removed and no empty or header-only pages remaining in the text scan or rendered page overviews. Chapters 1–6 still contain 38 content pages. No LaTeX errors, undefined citations/references, or overfull boxes. Source hashes confirm that all chapter, appendix, figure, and bibliography sources and `REDUCTION_PLAN.md` are unchanged; the abstract is unchanged as well, preserving all pilot material. Other pending notes remain open. |
| 2026-11-22 | Note 3: Context and Problem | Rewrote the opening of Section 1.1 around anticipated confrontation, anxiety, avoidance, and difficulty finding words. Explained private, repeatable rehearsal and reflection before introducing language models and technical control; stated explicitly that AffectLab does not diagnose or treat anxiety. | Rebuilt the 67-page PDF with no LaTeX errors, undefined citations/references, or overfull boxes. Visually checked the revised opening and following page; Section 1.1 fits on one page and Section 1.2 starts on the next. Source hashes confirm that Chapter 1 after Section 1.1, all other thesis sources, and REDUCTION_PLAN.md are unchanged, preserving all pilot material. Other pending notes remain open. |
| 2026-11-22 | Note 4: Equations | Replaced Chapter 2's causal-context notation with prose about the current and preceding turns, excluding future turns and annotated neighbouring labels. Replaced its duplicate fusion formula with a weighted-average explanation. Retained the implementation fusion equation and defined all distributions, the weight range, and equal weighting. Explained temperature scaling in prose, including validation-only NLL fitting and unchanged application to held-out test logits; removed the obsolete temperature-equation label. | Rebuilt the 67-page PDF with no LaTeX errors, undefined citations/references, or overfull boxes. Visually checked the affected pages and their continuations (numbered pages 8–9, 18–19, and 27–28). Confirmed that only one displayed equation remains, with no obsolete equation references, and checked the temperature-fitting account against the implementation. Citation commands are unchanged. Source comparisons confirm that all Chapter 5 results and pilot material, all other thesis sources, the bibliography, and REDUCTION_PLAN.md are unchanged. Other pending notes remain open. |
| 2026-11-22 | Note 5: Length audit and local reduction; partially addressed | Removed one repeated 64-word overview paragraph from Section 4.1, eliminating Chapter 4's sparse final continuation. Recorded the current page breakdown and the remaining dependencies on appendix reduction, prose consolidation, and readable replacement figures. | Rebuilt successfully: 66 physical pages and 37 chapter-content pages, down from 67 and 38 before this change. Visually checked numbered pages 16–23. No LaTeX errors, undefined citations/references, or overfull boxes; all 35 bibliography entries remain cited. Source hashes confirm that every other thesis source, figure, the bibliography, and REDUCTION_PLAN.md are unchanged; an exact source comparison confirms that all other Chapter 4 text, including pilot passages, is unchanged. Note 5 remains open for the remaining reductions and the final pagination review. |
| 2026-11-22 | Note 6: Opening of Section 3.2 | Replaced the specification-history opening with the capabilities users need: preparation, private rehearsal, feedback, control over data and optional features, text-only access, and clear interruption and service-failure handling. Introduced the nine requirement groups and FR/NFR identifiers after their purpose, with references to the full requirements and verification evidence. Removed editorial justification from the opening and the later acceptance-criteria explanation. | Rebuilt successfully: 66 physical pages and 37 chapter-content pages, unchanged. Visually checked numbered pages 12-15; the opening fits before the unchanged requirements table, with no sparse continuation page. No LaTeX errors, undefined citations/references, or overfull boxes. Source hashes and exact comparisons confirm that only Section 3.2 prose changed; all requirements, identifiers, citations, pilot material, other thesis sources, and REDUCTION_PLAN.md are unchanged. Other pending notes remain open. |
| 2026-11-22 | Note 7: Technical figures | Rebuilt Figures 3.1 and 4.1–4.3 with shared styles and native 10-point labels. Separated architecture connections, reduced the pipeline to seven boxes in two paths, reduced the request sequence to three lanes with a shared commit step, and separated pacing outcomes and lower emotion branches. Updated captions, List of Figures entries, and directly related discussion. | Rebuilt successfully: 67 physical pages and 38 chapter-content pages, one more than before because of readable Chapter 4 diagrams. Visually checked all 14 Chapter 3/4 pages and each diagram at 95 dpi; no overlaps, clipping, isolated figure page, or one-word continuation remains. No LaTeX errors, undefined citations/references, or overfull boxes; all 35 bibliography entries remain cited. Source hashes and exact comparisons confirm that pilot material, numerical findings, all other chapter text, other thesis sources, and REDUCTION_PLAN.md are unchanged. Note 5 and other pending notes remain open. |
