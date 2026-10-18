"""Build realistic local-development usage data without marking user-facing records."""

import argparse
import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from random import Random
from uuid import NAMESPACE_URL, UUID, uuid5

from pymongo import MongoClient
from pymongo.uri_parser import parse_uri

from app.core.config import settings
from app.models.domain import (
    Difficulty,
    PracticeGoal,
    RolePlayStatus,
    Session,
    StudyConsentRecord,
    StudyEligibilityRecord,
    StudyWithdrawalRecord,
    User,
    utcnow,
)
from app.repositories.memory import MemoryRepository
from app.repositories.mongo import MongoRepository
from app.services.auth_service import password_hash
from app.services.conversation_service import ConversationService
from app.services.eligibility import eligibility_version
from app.services.llm_service import TemplateResponseGenerator
from scripts.mongo_backup import backup_database

RANDOM_SEED = 20261016
PASSWORD = "AffectLabLocal2026!"
DATASET_VERSION = "local-usage-v1"
REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

PARTICIPANT_PROFILES = [
    ("Ana", "Popescu"), ("Mihai", "Ionescu"), ("Elena", "Dumitrescu"),
    ("Andrei", "Marinescu"), ("Ioana", "Radu"), ("Vlad", "Stan"),
    ("Cristina", "Matei"), ("Alexandru", "Pavel"), ("Diana", "Munteanu"),
    ("Radu", "Georgescu"), ("Maria", "Stoica"), ("Ștefan", "Ilie"),
    ("Bianca", "Tudor"), ("George", "Dobre"), ("Alina", "Preda"),
    ("Cătălin", "Nistor"), ("Larisa", "Mocanu"), ("Bogdan", "Enache"),
    ("Irina", "Voicu"), ("Sorin", "Diaconu"), ("Adriana", "Neagu"),
    ("Paul", "Sandu"), ("Denisa", "Lupu"), ("Florin", "Barbu"),
    ("Oana", "Costache"), ("Darius", "Petrescu"), ("Nicoleta", "Avram"),
    ("Victor", "Mihalache"), ("Simona", "Dragomir"), ("Rareș", "Grigore"),
    ("Mara", "Crăciun"), ("Lucian", "Oprea"),
]

STUDY_FIXTURE_PROFILES = PARTICIPANT_PROFILES[:17]

ORDINARY_PROFILES = [
    ("Teodora", "Moldovan"),
    ("Iulian", "Roman"),
    ("Monica", "Vasile"),
    ("Robert", "Manea"),
]

DIALOGUES = {
    "workload": [
        ["I'm struggling to keep up and wasn't sure how to bring this up.", "The report and client slides are both due Friday.", "Could you help me choose which deadline takes priority?"],
        ["I need some help with my workload.", "Could we move the internal report to Tuesday? The client meeting needs my attention first."],
        ["Everything feels urgent at the moment.", "I keep switching tasks and not finishing much.", "I want to agree on priorities.", "Specifically, can we postpone the report until Friday?"],
        ["I can complete the budget review or the presentation today, but not both.", "Which one should I finish first, and can the other move to tomorrow?"],
        ["The last-minute requests are making it difficult to finish the planned work.", "Can we review the deadlines and decide what can wait until next week?"],
        ["I want to flag a capacity issue before I miss a deadline.", "Could someone else take the meeting notes while I finish the client proposal?"],
    ],
    "boundary": [
        ["I understand this is important, but I cannot take it on this week.", "You will need to ask someone else or move the deadline."],
        ["I can't help this weekend; I already have plans.", "I understand the pressure, but I'm not able to change those plans."],
        ["I was tempted to say yes, but I need to be honest about my capacity.", "I cannot take responsibility for this again."],
        ["I can stay for another fifteen minutes, but then I need to leave.", "Anything unfinished will have to wait until Monday."],
        ["I'm not comfortable discussing that in front of the whole team.", "We can talk privately after the meeting instead."],
        ["I can help you review the first page, but I can't rewrite the whole document tonight.", "Please send the section you are most worried about."],
    ],
    "relationship": [
        ["I feel a bit distant from you lately.", "I would like us to spend more time together.", "Could we set aside one evening each week to talk without our phones?"],
        ["That came out more sharply than I intended.", "I feel lonely and I want more time together.", "Could you join me for a walk on Tuesday evening?"],
        ["I am nervous about saying this.", "I miss feeling close to you.", "I would like twenty minutes together after dinner, because lately we just look at our phones."],
        ["I felt overlooked when our plans changed without us talking.", "Can we check with each other before committing to weekend plans?"],
        ["I care about us, and I don't want this to turn into an argument.", "Could we talk for half an hour tomorrow when we are both rested?"],
        ["When messages go unanswered for days, I start to feel disconnected.", "Could we agree to send a quick note when one of us is busy?"],
    ],
    "deadline": [
        ["I am concerned about delivery.", "Could you approve Tuesday instead of Friday so we have time to test the changes?"],
        ["Friday is possible only if we cut the review step.", "I'd prefer Monday so we can check the work properly."],
    ],
}

TAKEAWAYS = [
    "Ask which task can wait instead of promising to finish everything.",
    "I can acknowledge the request without changing my answer.",
    "Give a concrete suggestion instead of expecting the other person to guess.",
    "Pause before explaining; one clear sentence is enough.",
    "Name the impact and make one specific request.",
    "Leave room for a response after stating the boundary.",
]

REFLECTIONS = [
    "I have a difficult meeting tomorrow and I keep imagining it going badly.",
    "I agreed to too much this week and now I need to reset expectations.",
    "A friend cancelled again and I want to respond without sounding accusatory.",
    "I need to ask for clearer feedback instead of guessing what my manager wants.",
]


def stable_uuid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"https://affectlab.invalid/local-development/{value}")


def profile_email(first: str, last: str, index: int) -> str:
    replacements = str.maketrans({"ă": "a", "â": "a", "î": "i", "ș": "s", "ț": "t", "Ă": "A", "Â": "A", "Î": "I", "Ș": "S", "Ț": "T"})
    local = f"{first}.{last}".translate(replacements).lower().replace(" ", "-")
    return f"{local}.{index + 1:02d}@example.com"


def ensure_local_development_target() -> None:
    if settings.environment.strip().lower() != "development":
        raise ValueError("The usage-data seeder runs only when ENVIRONMENT=development")
    if settings.mongodb_uri.lower().startswith("mongodb+srv://"):
        raise ValueError("The usage-data seeder refuses SRV and remote MongoDB targets")
    hosts = {host.lower().strip("[]") for host, _ in parse_uri(settings.mongodb_uri)["nodelist"]}
    if not hosts or not hosts.issubset({"localhost", "127.0.0.1", "::1"}):
        raise ValueError(f"The usage-data seeder requires local MongoDB; found {sorted(hosts)}")
    if settings.mongodb_database in {"admin", "config", "local"}:
        raise ValueError("Refusing to seed a MongoDB system database")


def retime(session: Session, start: datetime, duration: int) -> Session:
    """Move generated events onto a plausible historical timeline."""
    data = session.model_dump()
    times = set()

    def collect(value):
        if isinstance(value, datetime):
            times.add(value)
        elif isinstance(value, dict):
            for key, item in value.items():
                if key != "expires_at":
                    collect(item)
        elif isinstance(value, list):
            for item in value:
                collect(item)

    collect(data)
    ordered = sorted(times)
    mapping = {
        value: start + timedelta(seconds=duration * i / max(1, len(ordered) - 1))
        for i, value in enumerate(ordered)
    }

    def replace(value):
        if isinstance(value, datetime):
            return mapping.get(value, value)
        if isinstance(value, dict):
            return {key: replace(item) for key, item in value.items()}
        if isinstance(value, list):
            return [replace(item) for item in value]
        return value

    result = Session.model_validate(replace(data))
    result.expires_at = result.updated_at + timedelta(days=settings.session_retention_days)
    return result


async def add_rehearsal(
    service: ConversationService,
    repository: MemoryRepository,
    user: User,
    scenario: str,
    purpose: str,
    cursor: datetime,
    rng: Random,
    *,
    required_task: str | None = None,
    outcome: str = "complete",
    ratings_skipped: bool = False,
) -> tuple[datetime, Session]:
    session = await service.create_session(user.id)
    pre_skipped = rng.random() < 0.08
    pre_confidence = rng.choices([2, 3, 4, 5, 6], weights=[2, 5, 8, 5, 2])[0]
    pre = {"confidence": pre_confidence, "anxiety": rng.choices([2, 3, 4, 5, 6, 7], [1, 3, 6, 7, 4, 1])[0]}
    difficulty = Difficulty.INTERMEDIATE if purpose in {"required", "retry"} else rng.choice(list(Difficulty))
    session, _, _ = await service.start_roleplay(
        session.id,
        user.id,
        scenario,
        difficulty,
        pre_ratings=None if pre_skipped else pre,
        pre_skipped=pre_skipped,
        attempt_purpose=purpose,
        required_task_id=required_task,
    )
    messages = (
        ["I'm not sure how to put this into words yet."]
        if outcome in {"active", "paused"}
        else DIALOGUES[scenario][rng.randrange(len(DIALOGUES[scenario]))]
    )
    for message in messages:
        _, _, session = await service.chat(session.id, user.id, message)
        if session.roleplay.status == RolePlayStatus.COMPLETED:
            break
    if outcome == "paused" and session.roleplay.status == RolePlayStatus.ACTIVE:
        session = await service.set_roleplay_status(session.id, user.id, "pause")
    elif outcome == "complete" and session.roleplay.status == RolePlayStatus.ACTIVE:
        # Protocol v1.1 does not count a manual finish as primary completion.
        # Complete designated fixture paths through the deterministic controller.
        completion_turn = {
            "workload": "I need you to prioritise the deadline because it is Friday.",
            "boundary": "I cannot take this on; I need to say no.",
            "relationship": "I need twenty minutes together this evening.",
            "deadline": "I need the deadline moved to Friday because I need 3 more hours.",
        }[scenario]
        while session.roleplay.status == RolePlayStatus.ACTIVE:
            _, _, session = await service.chat(session.id, user.id, completion_turn)
    if session.roleplay.status == RolePlayStatus.COMPLETED:
        confidence_change = rng.choices([-1, 0, 1, 2, 3], [2, 7, 10, 7, 2])[0]
        values = {} if ratings_skipped else {
            "confidence": max(1, min(7, pre_confidence + confidence_change)),
            "realism": rng.choices([3, 4, 5, 6, 7], [2, 7, 11, 7, 2])[0],
            "usefulness": rng.choices([3, 4, 5, 6, 7], [1, 5, 10, 9, 3])[0],
        }
        await service.submit_questionnaire(
            session.id,
            user.id,
            "post",
            values,
            skipped=ratings_skipped,
            post_token=session.post_questionnaire_token,
        )
        if rng.random() < 0.72:
            await service.save_takeaway(session.id, user.id, rng.choice(TAKEAWAYS))
    session = await service.get_session(session.id, user.id)
    duration = rng.randint(190, 880)
    session = retime(session, cursor, duration)
    await repository.save_session(session)
    await service.sync_study_record(session)
    return cursor + timedelta(seconds=duration + rng.randint(90, 1_200)), session


async def build_cohort() -> MemoryRepository:
    repository = MemoryRepository()
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    rng = Random(RANDOM_SEED)
    shared_hash = password_hash.hash(PASSWORD)
    base = utcnow() - timedelta(days=27)

    for index, (first, last) in enumerate(STUDY_FIXTURE_PROFILES):
        enrolled = base + timedelta(hours=index * 14, minutes=rng.randint(0, 80))
        user = User(
            id=stable_uuid(f"participant-user/{index}"),
            participant_id=stable_uuid(f"participant/{index}"),
            email=profile_email(first, last, index),
            password_hash=shared_hash,
            first_name=first,
            last_name=last,
            preferred_name=first,
            country="Romania",
            timezone="Europe/Bucharest",
            consented_at=enrolled - timedelta(minutes=rng.randint(3, 18)),
            consent_version=settings.research_consent_version,
            email_verified_at=enrolled - timedelta(minutes=rng.randint(1, 3)),
            onboarding_completed_at=enrolled,
            onboarding_version=settings.onboarding_version,
            practice_goals=rng.sample(list(PracticeGoal), k=rng.choice([1, 1, 2, 2, 3])),
            pilot_enrolled_at=enrolled,
            study_consent=StudyConsentRecord(
                version=settings.study_consent_version,
                protocol_version=settings.study_protocol_version,
                accepted_at=enrolled,
            ),
            study_eligibility=StudyEligibilityRecord(
                version=eligibility_version(),
                protocol_version=settings.study_protocol_version,
                confirmed_at=enrolled,
            ),
            created_at=enrolled - timedelta(minutes=rng.randint(5, 40)),
        )
        await repository.create_user(user)
        cursor = enrolled + timedelta(minutes=rng.randint(3, 90))

        if index <= 12:
            tasks = ["workload", "boundary", "relationship"]
        elif index in {13, 15, 16}:
            tasks = ["workload", "boundary"]
        elif index == 14:
            tasks = ["workload"]
        else:
            tasks = []

        for task in tasks:
            outcome = "complete"
            ratings_skipped = index == 12 and task == "relationship"
            if index == 13 and task == "boundary":
                outcome = "paused"
            if index == 14 and task == "workload":
                outcome = "active"
            cursor, _ = await add_rehearsal(
                service,
                repository,
                user,
                task,
                "required",
                cursor,
                rng,
                required_task=task,
                outcome=outcome,
                ratings_skipped=ratings_skipped,
            )
            if outcome != "complete":
                break

        if index < 13 and index % 6 == 1:
            cursor, _ = await add_rehearsal(
                service,
                repository,
                user,
                "boundary",
                "retry",
                cursor + timedelta(days=rng.randint(1, 3)),
                rng,
                required_task="boundary",
            )
        if index < 13 and index % 8 == 3:
            cursor, _ = await add_rehearsal(
                service,
                repository,
                user,
                "deadline",
                "additional",
                cursor + timedelta(hours=rng.randint(4, 30)),
                rng,
            )

    excluded = await repository.get_user(stable_uuid("participant-user/15"))
    assert excluded is not None
    excluded.study_excluded_at = utcnow() - timedelta(days=2)
    excluded.study_exclusion_reason = "Duplicate enrollment identified during review"
    excluded.study_data_quality_notes = "Two sessions were retained for the participant-level review trail."
    await repository.save_user(excluded)

    withdrawn = await repository.get_user(stable_uuid("participant-user/16"))
    assert withdrawn is not None and withdrawn.study_consent is not None
    withdrawn.study_withdrawal = StudyWithdrawalRecord(
        withdrawn_at=utcnow() - timedelta(days=1),
        consent_version=withdrawn.study_consent.version,
    )
    await repository.save_user(withdrawn)
    await repository.delete_study_records(withdrawn.id)

    for index, (first, last) in enumerate(ORDINARY_PROFILES):
        joined = base + timedelta(days=8 + index * 3, hours=rng.randint(1, 20))
        user = User(
            id=stable_uuid(f"ordinary-user/{index}"),
            participant_id=stable_uuid(f"ordinary-participant/{index}"),
            email=profile_email(first, last, len(STUDY_FIXTURE_PROFILES) + index),
            password_hash=shared_hash,
            first_name=first,
            last_name=last,
            preferred_name=first,
            country="Romania",
            timezone="Europe/Bucharest",
            consented_at=joined,
            consent_version=settings.research_consent_version,
            email_verified_at=joined,
            onboarding_completed_at=joined + timedelta(minutes=4),
            onboarding_version=settings.onboarding_version,
            practice_goals=rng.sample(list(PracticeGoal), k=rng.choice([1, 2])),
            created_at=joined,
        )
        await repository.create_user(user)
        session = await service.create_session(user.id)
        _, _, session = await service.chat(session.id, user.id, REFLECTIONS[index])
        session = retime(session, joined + timedelta(hours=2), rng.randint(160, 420))
        await repository.save_session(session)

    researcher_email = next(
        (item.strip() for item in settings.researcher_emails.split(",") if item.strip()),
        settings.study_researcher_email,
    )
    researcher = User(
        id=stable_uuid("researcher-user"),
        participant_id=stable_uuid("researcher-participant"),
        email=researcher_email,
        password_hash=shared_hash,
        first_name=settings.study_researcher_name.split()[0] or "Raluca",
        last_name=" ".join(settings.study_researcher_name.split()[1:]) or "Biras",
        preferred_name=settings.study_researcher_name.split()[0] or "Raluca",
        country="Romania",
        timezone="Europe/Bucharest",
        consented_at=base,
        consent_version=settings.research_consent_version,
        email_verified_at=base,
        onboarding_completed_at=base,
        onboarding_version=settings.onboarding_version,
        practice_goals=[PracticeGoal.PREPARE_CONVERSATION],
        created_at=base,
    )
    if await repository.get_user_by_email(researcher.email) is None:
        await repository.create_user(researcher)
    return repository


def backup_path() -> Path:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    return REPOSITORY_ROOT / ".local" / "database-backups" / stamp


def backup_current_database() -> str | None:
    client = MongoClient(settings.mongodb_uri, uuidRepresentation="standard")
    try:
        database = client[settings.mongodb_database]
        if not database.list_collection_names():
            return None
    finally:
        client.close()
    destination = backup_path()
    backup_database(settings.mongodb_uri, settings.mongodb_database, destination)
    return str(destination)


def drop_current_database() -> None:
    client = MongoClient(settings.mongodb_uri, uuidRepresentation="standard")
    try:
        client.drop_database(settings.mongodb_database)
    finally:
        client.close()


async def write_fixtures(fixtures: MemoryRepository) -> dict[str, int | str]:
    repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
    await repository.initialize()
    try:
        users = await fixtures.list_users()
        sessions = records = 0
        for user in users:
            await repository.create_user(user)
            for session in await fixtures.list_sessions(user.id):
                # These fully materialized sessions already carry realistic
                # concurrency versions from their in-memory service history.
                await repository.db.sessions.insert_one(session.model_dump(mode="python"))
                sessions += 1
            for record in await fixtures.list_study_records(user.id):
                await repository.save_study_record(record)
                records += 1
        await repository.db.development_metadata.insert_one({
            "_id": "usage-seed-provenance",
            "dataset_type": "simulated",
            "environment": "development",
            "scope": "local-only",
            "generator": "backend.scripts.seed_mock_data",
            "generator_version": DATASET_VERSION,
            "random_seed": RANDOM_SEED,
            "contains_observed_participant_data": False,
            "created_at": utcnow(),
        })
        return {
            "users": len(users),
            "sessions": sessions,
            "study_records": records,
            "metadata_records": 1,
            "database": settings.mongodb_database,
        }
    finally:
        await repository.client.close()


async def seed_empty_database() -> dict[str, int | str]:
    ensure_local_development_target()
    fixtures = await build_cohort()
    client = MongoClient(settings.mongodb_uri, uuidRepresentation="standard")
    try:
        database = client[settings.mongodb_database]
        existing = sum(database[name].count_documents({}) for name in database.list_collection_names())
        if existing:
            raise ValueError("Database is not empty. Use the reset command to back it up, clear it, and seed it.")
    finally:
        client.close()
    return await write_fixtures(fixtures)


async def reset_and_seed() -> dict:
    ensure_local_development_target()
    fixtures = await build_cohort()  # Validate every fixture before deleting anything.
    backup = backup_current_database()
    drop_current_database()
    result = await write_fixtures(fixtures)
    return {"backup": backup, "reset": True, **result}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("reset", "seed", "clear"), nargs="?", default="reset")
    args = parser.parse_args()
    ensure_local_development_target()
    if args.command == "reset":
        result = asyncio.run(reset_and_seed())
    elif args.command == "seed":
        result = asyncio.run(seed_empty_database())
    else:
        backup = backup_current_database()
        drop_current_database()
        result = {"backup": backup, "cleared": True, "database": settings.mongodb_database}
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
