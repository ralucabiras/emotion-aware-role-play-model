# Remote pilot security and safety baseline

This document separates local dissertation demonstrations from any deployment accessible to participants. The remote-pilot controls below are mandatory before issuing participant access codes.

## Participant scope and emergency boundary

- Supported language: English only. Affect and crisis rules have not been validated for other languages.
- Minimum participant age: 18.
- Geographic scope: participants located in Romania.
- AffectLab is not therapy, medical advice, diagnosis, crisis monitoring, or an emergency service.
- The service is not continuously monitored, cannot determine a participant's location, and cannot contact emergency services. In immediate danger, participants should call 112 in Romania or their applicable local emergency number and seek human help.
- The lexical crisis detector is deliberately limited. OpenAI moderation is secondary when configured, but neither mechanism guarantees detection. Ambiguous distress that does not meet the lexical threshold may not interrupt a conversation.

These restrictions must appear in recruitment material, the information sheet, consent discussion, and demonstration script. Expanding language, age, or geography requires protocol review and new safety validation.

## Required production configuration

Set `ENVIRONMENT=production`. Startup then fails unless all of these are true:

- `JWT_SECRET` is a unique random secret of at least 32 bytes and is not a documented default.
- `CORS_ALLOWED_ORIGINS` contains only explicit HTTPS origins, with no wildcard.
- `TRUSTED_HOSTS` lists the API host names, with no wildcard.
- `ENFORCE_HTTPS=true` and the reverse proxy passes the original scheme correctly.
- `RATE_LIMIT_ENABLED=true`.

Terminate TLS at a maintained reverse proxy or managed platform, redirect HTTP to HTTPS, and restrict direct access to MongoDB and the application server. Refresh cookies become `Secure` automatically outside development. HSTS and restrictive response headers are also enabled.

The built-in rate limiter is suitable for the planned single-process pilot. It is process-local and deliberately ignores forwarded IP headers. A multi-worker or multi-instance deployment must put a shared limiter at the trusted reverse proxy or use a shared Redis-backed limiter.

## Backup and restore drill

Backups contain sensitive personal data. Store them encrypted, access-controlled, in a location separate from the application host, and delete them according to the approved retention schedule.

Create a BSON-preserving backup:

```powershell
cd backend
..\.venv\Scripts\python.exe scripts\mongo_backup.py backup --uri "mongodb://localhost:27017" --database affectlab --destination "D:\secure-backups\affectlab-2026-09-22"
```

Verify restoration into an empty disposable database (the safety suffix is required):

```powershell
..\.venv\Scripts\python.exe scripts\mongo_backup.py restore-test --uri "mongodb://localhost:27017" --source "D:\secure-backups\affectlab-2026-09-22" --target-database affectlab_20260922_restore_test
```

The restore verifies archive checksums and collection document counts and recreates collection indexes. Record the drill date, operator, backup identifier, restored counts, and deletion of the test database. Run a drill before recruitment and at least once during data collection.

## Dependency and operational checks

GitHub Actions audits production Python dependencies and npm packages weekly and on changes. Dependabot opens weekly dependency updates. Before deployment, run:

```powershell
cd backend
..\.venv\Scripts\python.exe -m pip_audit -r requirements.txt

cd ..\frontend
npm audit --audit-level=high
```

Do not deploy with unresolved high or critical findings. Keep host OS, MongoDB, reverse proxy, Python, and Node patched; these are outside repository-level scanning.

