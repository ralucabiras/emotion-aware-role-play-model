# Local development dataset

From `backend`, run:

```powershell
../.venv/Scripts/python.exe -m scripts.seed_mock_data reset
```

`reset` is intentionally destructive to the configured application database. It first validates the complete replacement dataset in memory, verifies that `ENVIRONMENT=development` and every MongoDB host is local, writes a BSON-preserving backup under ignored `.local/database-backups/`, drops the configured database, recreates its indexes, and inserts the new data. The command removes prior accounts, sessions, authentication tokens, study records, lifecycle settings, and frozen exports. `seed` works only with an empty database. `clear` backs up and drops the database without reseeding it.

The dataset contains 17 enrolled accounts—15 in the active analysis cohort, one withdrawn, and one excluded—plus four ordinary application accounts and one researcher account. It mirrors the protocol v1.1 enrollment target and covers complete and incomplete task sequences, an active rehearsal, a paused rehearsal, missing ratings, retries, additional practice, withdrawal, exclusion, saved takeaways, and ordinary reflections. Dates span recent weeks and remain inside configured retention windows. Conversations, feedback evidence, questionnaire records, source counts, and relationships are produced through the current application services without external model calls.

Names, session titles, notes, and results are presented exactly as normal application data. They do not carry fixture prefixes or labels. The sole provenance marker is the development-only `development_metadata` collection, whose `usage-seed-provenance` document records the generator version, fixed random seed, local scope, and that the observations are simulated. This collection is not exposed by the application API or UI.

All generated accounts share the local password `AffectLabLocal2026!`. Participant addresses use the reserved `example.com` domain. The researcher address is the first address in `RESEARCHER_EMAILS`, allowing the researcher dashboard to be tested with the same local password.

These records are for local functional testing and visualization only. They are not observed participant outcomes or research findings. Run `clear` before collecting real data, verify that the application database is empty, and remove local database backups when they are no longer needed.
