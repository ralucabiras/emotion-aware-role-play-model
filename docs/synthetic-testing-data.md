# Synthetic testing dataset

Run from `backend`: `../.venv/Scripts/python.exe -m scripts.seed_mock_data seed`.
This replaces only the known synthetic accounts and tagged synthetic sessions in the configured database. It no longer adds sessions to a real/researcher account. Before replacement, affected documents (including authentication tokens) are backed up under ignored `.local/seed-backups/`; keep these local and private. `clear` backs up and removes the same fixtures. Frozen databases are not reseeded.

The ten existing example.com accounts use password `affectlab-synthetic-demo`. Names remain natural for interface testing; session titles, account quality notes, and research events identify synthetic origin. These accounts remain included in the current testing dashboard and exports.

Cases include six complete three-task procedures, one procedure with a skipped post-questionnaire, one paused second task, one active first task, and one enrollment without activity. Two separate retries and one additional deadline practice exercise history/comparison and primary-attempt selection. A successful retry does not repair the skipped required questionnaire. Pre-questionnaire skips and manual finish are also covered.

Required tasks run workload, boundary, relationship at intermediate difficulty. Conversation, evidence, scores, feedback, purpose associations, questionnaires and source counts are produced through the current application services without external model calls. Scripted wording, ratings and wall times are constructed fixtures. Ratings include unchanged and lower confidence as well as increases. A fixed random seed makes case variation reproducible; timestamps are relative to execution, with enrollment preceding activity. Generator sources truthfully record deterministic/template behavior, not OpenAI generation.

Use these data for functional testing and clearly identified synthetic illustrations only. They are not observed participant outcomes or an estimate of likely study results. Wipe the test dataset before participant collection; do not merge it with collected results. Local backups remain after clearing the database and should also be removed when no longer needed.
