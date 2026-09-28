# Personal conversation preparation and action cards

Implemented 28 September 2026. In Role-play setup select **Prepare a real conversation**. After a completed or interrupted rehearsal, select **Action card**.

## Preparation

The form asks who you will speak with, what happened, your desired outcome and the difficult part. Descriptions such as “my manager” or “my housemate” are sufficient; names and identifying details are not required.

`POST /api/roleplay/preparation` validates these four inputs and returns an unsaved template brief. It does not start a rehearsal or write to the account. The review screen exposes the title, role, situation, objective, opening line, possible objection, difficult part and practice focus. The focus offers request, boundary and need templates with participant-friendly descriptions of their supported language features.

The user edits and confirms the brief before it is saved through the existing custom-scenario endpoint. **Use offline template** works without the preparation endpoint; network or save failures preserve the form so it can be retried. Saving a brief still requires the backend. Template generation is deterministic in this release; there is no online LLM brief-generation path or claim of personalised prediction. Both the server and offline fallback label the possible objection as a practice prompt, not knowledge of another person's intentions.

Saved custom scenarios have an **Edit brief** action, including older records without preparation metadata. `PUT /api/roleplay/scenarios/{id}` updates only a custom scenario owned by the current user. Editing an old custom scenario through this form adds a reviewed preparation brief for future attempts. Existing rehearsal history uses its own scenario snapshot and is unchanged. Custom briefs use the existing account storage/deletion lifecycle, not the session expiry clock; the form discloses this. Brief edits follow the existing user-profile persistence model and do not provide per-brief revision history.

## Supported rehearsal behavior

Prepared briefs use a bounded generic flow: explain the situation, respond to a possible objection, then review the wording. They do not receive the three core scenarios' specialised dialogue stages, profiles or agreement rules. The interface discloses these limits.

New prepared sessions record `scenario_version=prepared-brief-v1`, `policy_version=prepared-generic-v1` and `scoring_version=prepared-features-v1`. Their first response uses the reviewed objection verbatim and cannot immediately complete the rehearsal. Subsequent completion requires the selected generic language features plus a relevant feature in the current reply; unrelated text alone cannot finish an already-qualified opening. The ordinary turn cap, manual finish, pause and safety handling remain available. Completion means the generic feature requirements were met, not that an external person agreed.

Character wording for prepared sessions is deterministic. Existing moderation, where configured, remains independent. Unprepared legacy custom scenarios keep their previous behavior. Required study tasks retain their frozen controller. Prepared generic scenarios have no enhanced dialogue snapshots, so Step 5 branching remains unavailable for them; replay can show their transcript and available evidence without inventing decisions.

## Action cards

The action card has four editable fields: opening sentence, main request, boundary/fallback and one reminder. `GET /api/sessions/{id}/action-card` returns the saved card or an unsaved template suggestion with the current session version. Suggestions use the chosen objective and recorded user wording inside the rehearsal measurement boundary. They do not turn assistant replies or a simulated agreement into commitments. Later reflection is excluded; branches use only new user responses when choosing suggested wording. Interrupted crisis wording is not recycled into a card. Legacy records without a reliable completion boundary use general suggestions rather than copying uncertain transcript context.

Every screen and copied/downloaded text labels the wording as a draft for review. The user can edit any field and copy or download the current text without saving. Clipboard failure has an explicit message and leaves download/manual copying available. Text download produces `conversation-action-card.txt`; a print layout is not included.

`PUT /api/sessions/{id}/action-card` requires the expected session version and validates field lengths/nonblank text. It writes a separate `Session.action_card` with source/provenance and update time, without changing feedback, ratings, events or completed measurement boundaries. Stale saves return 409. **Refresh saved version and keep my draft** preserves local edits and explains that the next save replaces the current saved card. A response from an unmounted editor cannot change a different session's client version.

Cards follow the session's ownership, retention and deletion rules. Account deletion removes them with sessions. A new branch does not inherit the parent's card. Rewind clears the card to avoid treating a plan based on discarded dialogue as current. Card text, preparation inputs and scenario wording are not added to research exports; no export-schema change is required.

## Synthetic demonstration

1. Enter “my housemate”, “I have been doing the dishes every evening this week”, “I would like us to share the dishes on weekdays”, and “I worry they will feel blamed”.
2. Review the brief. Change the possible objection to “I also have a busy week. What do you suggest?” and confirm it.
3. Start the rehearsal and say “I need help with the dishes this week.” The recorded objection is presented before completion.
4. Reply “Could you do the dishes on Monday?” Then review the recorded language feedback.
5. Open Action card and edit the opening to “Could we talk tonight about sharing the dishes?” Review the request and fallback in your own words, save, reload, and download the text.

These are authored engineering examples, not participant outcomes or evidence of communication improvement. Browser fixtures test the user flow and recovery; real MongoDB tests reload stored briefs, scenario snapshots and cards through a new repository/service instance. A full-stack browser/backend-process restart demonstration remains part of Step 7.
