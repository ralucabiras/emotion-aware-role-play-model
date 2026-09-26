"""Participant-like synthetic test fixtures; never observed research outcomes."""
import argparse
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from random import Random
from uuid import NAMESPACE_URL, UUID, uuid5

from bson import json_util
from bson.binary import UuidRepresentation

from app.core.config import settings
from app.models.domain import (
    Difficulty,
    PracticeGoal,
    ResearchEvent,
    RolePlayStatus,
    Session,
    StudyConsentRecord,
    StudyEligibilityRecord,
    User,
    utcnow,
)
from app.repositories.memory import MemoryRepository
from app.repositories.mongo import MongoRepository
from app.services.auth_service import password_hash
from app.services.conversation_service import ConversationService
from app.services.eligibility import eligibility_version
from app.services.llm_service import TemplateResponseGenerator

PASSWORD = "affectlab-synthetic-demo"
PROFILES = [
    ("Ana", "Popescu", "ana.popescu@example.com", "Bucharest"),
    ("Mihai", "Ionescu", "mihai.ionescu@example.com", "Cluj-Napoca"),
    ("Elena", "Dumitrescu", "elena.dumitrescu@example.com", "Iași"),
    ("Andrei", "Marinescu", "andrei.marinescu@example.com", "Timișoara"),
    ("Ioana", "Radu", "ioana.radu@example.com", "Brașov"),
    ("Vlad", "Stan", "vlad.stan@example.com", "Constanța"),
    ("Cristina", "Matei", "cristina.matei@example.com", "Sibiu"),
    ("Alexandru", "Pavel", "alexandru.pavel@example.com", "Oradea"),
    ("Diana", "Munteanu", "diana.munteanu@example.com", "Craiova"),
    ("Radu", "Georgescu", "radu.georgescu@example.com", "Ploiești"),
]
def stable_uuid(value: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"https://affectlab.invalid/synthetic/{value}")


async def clear_seeded(repository: MongoRepository) -> dict[str, int]:
    mock_ids = [stable_uuid(f"user/{index}") for index in range(len(PROFILES))]
    owned_sessions = await repository.db.sessions.find({"research_events.name": "synthetic_seed"}, {"id": 1}).to_list(None)
    session_ids = [item["id"] for item in owned_sessions]
    sessions = await repository.db.sessions.delete_many({"$or": [{"user_id": {"$in": mock_ids}}, {"id": {"$in": session_ids}}]})
    records = await repository.db.study_records.delete_many({"$or": [{"user_id": {"$in": mock_ids}}, {"session_id": {"$in": session_ids}}]})
    users = await repository.db.users.delete_many({"id": {"$in": mock_ids}})
    for collection in ("refresh_tokens", "email_verification_tokens", "password_reset_tokens"):
        await repository.db[collection].delete_many({"user_id": {"$in": mock_ids}})
    return {"users": users.deleted_count, "sessions": sessions.deleted_count, "study_records": records.deleted_count}


# Deliberately authored test cases, not a simulated estimate of treatment effects.
DIALOGUES = {
    "workload": [
        ["I'm struggling to keep up and wasn't sure how to bring this up.", "The report and client slides are both due Friday.", "Could you help me choose which deadline takes priority?"],
        ["I need some help with my workload.", "Could you move the internal report to Tuesday? The client meeting needs my attention first."],
        ["Everything feels urgent at the moment.", "I keep switching tasks and not finishing much.", "I want to agree on priorities.", "Specifically, can we postpone the report until Friday?"],
    ],
    "boundary": [
        ["I'm sorry, sorry, I feel bad letting you down.", "I cannot take this on this week.", "I know it's inconvenient, but I can't do it. You will need to ask someone else."],
        ["I can't help this weekend; I already have plans.", "I understand, but I'm not able to change those plans."],
        ["Maybe, although I have a lot going on.", "Actually, I need to say no.", "I cannot take responsibility for this again."],
    ],
    "relationship": [
        ["I feel a bit distant from you lately.", "I would like us to spend more time together.", "Could we set aside one evening each week to talk without our phones?"],
        ["You never listen to me.", "That came out badly. I feel lonely and I want more time together.", "Could you join me for a walk on Tuesday evening?"],
        ["I am nervous about saying this.", "I miss feeling close to you.", "I would like twenty minutes together after dinner, because lately we just look at our phones."],
    ],
    "deadline": [["I am concerned about delivery.", "Could you approve Tuesday instead of Friday so we have time to test the changes?"]],
}
TAKEAWAYS = [
    "Ask which task can wait instead of promising to finish everything.",
    "I can acknowledge the request without changing my answer.",
    "Give a concrete suggestion instead of expecting the other person to guess.",
    "Pause before explaining; one clear sentence is enough.",
]


def retime(session: Session, start: datetime, duration: int) -> Session:
    """Assign constructed wall times, preserving the service's event ordering."""
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
    mapping = {value: start + timedelta(seconds=duration * i / max(1, len(ordered)-1))
               for i, value in enumerate(ordered)}
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


async def build_cohort():
    repository = MemoryRepository()
    service = ConversationService(repository, generator=TemplateResponseGenerator())
    rng = Random(20260926)
    shared_hash = password_hash.hash(PASSWORD)
    # Recent dates keep fixtures within retention and after the frozen protocol.
    base = utcnow() - timedelta(hours=48)
    for index, (first, last, email, city) in enumerate(PROFILES):
        enrolled = base + timedelta(hours=index * 3, minutes=rng.randint(0, 20))
        user = User(
            id=stable_uuid(f"user/{index}"), participant_id=stable_uuid(f"participant/{index}"),
            email=email, password_hash=shared_hash, first_name=first, last_name=last,
            preferred_name=first, country=f"Romania / {city}", timezone="Europe/Bucharest",
            consented_at=enrolled, consent_version=settings.research_consent_version,
            email_verified_at=enrolled, onboarding_completed_at=enrolled,
            onboarding_version=settings.onboarding_version,
            practice_goals=[list(PracticeGoal)[index % len(PracticeGoal)]],
            pilot_enrolled_at=enrolled,
            study_consent=StudyConsentRecord(version=settings.study_consent_version,
                protocol_version=settings.study_protocol_version, accepted_at=enrolled),
            study_eligibility=StudyEligibilityRecord(version=eligibility_version(),
                protocol_version=settings.study_protocol_version, confirmed_at=enrolled),
            study_data_quality_notes="SYNTHETIC testing fixture: constructed conversations, ratings and eligibility; not participant evidence.",
            created_at=enrolled - timedelta(minutes=rng.randint(4, 15)),
        )
        await repository.create_user(user)
        cursor = enrolled + timedelta(minutes=rng.randint(2, 7))
        tasks = ["workload", "boundary", "relationship"] if index < 7 else (["workload", "boundary"] if index == 7 else (["workload"] if index == 8 else []))
        attempts = [(task, "required") for task in tasks]
        if index in (1, 6):
            attempts.append(("boundary", "retry"))
        if index == 3:
            attempts.append(("deadline", "additional"))
        for offset, (task, purpose) in enumerate(attempts):
            session = await service.create_session(user.id)
            pre_skip = (index, offset) in {(4, 1), (7, 0)}
            pre = {"confidence": rng.randint(2, 6), "anxiety": rng.randint(2, 7)}
            session, _, _ = await service.start_roleplay(
                session.id, user.id, task, Difficulty.INTERMEDIATE,
                pre_ratings=None if pre_skip else pre, pre_skipped=pre_skip,
                attempt_purpose=purpose, required_task_id=task if purpose != "additional" else None,
            )
            session.research_events.insert(0, ResearchEvent(name="synthetic_seed", created_at=session.created_at,
                properties={"fixture_version": "participant-like-v2", "constructed": True}))
            await service.save(session)
            messages = DIALOGUES[task][(index + offset) % len(DIALOGUES[task])]
            paused = index == 7 and task == "boundary"
            active = index == 8
            manual = index == 5 and task == "relationship"
            for message in messages[:1] if paused or active or manual else messages:
                _, _, session = await service.chat(session.id, user.id, message)
                if session.roleplay.status == RolePlayStatus.COMPLETED:
                    break
            if paused:
                session = await service.set_roleplay_status(session.id, user.id, "pause")
            elif not active and session.roleplay.status == RolePlayStatus.ACTIVE:
                session = await service.set_roleplay_status(session.id, user.id, "finish")
            if session.roleplay.status == RolePlayStatus.COMPLETED:
                skip = index == 6 and purpose == "required" and task == "boundary"
                values = {} if skip else {
                    "confidence": max(1, min(7, pre["confidence"] + rng.choice([-1, 0, 0, 1, 1, 2]))),
                    "realism": rng.choice([3, 4, 4, 5, 5, 6, 7]),
                    "usefulness": rng.choice([3, 4, 5, 5, 6, 6, 7]),
                }
                await service.submit_questionnaire(session.id, user.id, "post", values,
                    skipped=skip, post_token=session.post_questionnaire_token)
                if (index + offset) % 3 != 0:
                    await service.save_takeaway(session.id, user.id, TAKEAWAYS[(index + offset) % len(TAKEAWAYS)])
            session = await service.get_session(session.id, user.id)
            session.title = "[Synthetic] " + session.title
            duration = rng.randint(180, 540)
            session = retime(session, cursor, duration)
            await repository.save_session(session)
            await service.sync_study_record(session)
            cursor += timedelta(seconds=duration + rng.randint(60, 240))
    return repository


async def backup_seeded(repository):
    ids = [stable_uuid(f"user/{i}") for i in range(len(PROFILES))]
    sessions = await repository.db.sessions.find({"$or": [
        {"user_id": {"$in": ids}}, {"research_events.name": "synthetic_seed"}]}).to_list(None)
    session_ids = [item["id"] for item in sessions]
    data = {"sessions": sessions}
    for name in ("users", "study_records", "refresh_tokens", "email_verification_tokens", "password_reset_tokens"):
        query = {"id" if name == "users" else "user_id": {"$in": ids}}
        if name == "study_records":
            query = {"$or": [query, {"session_id": {"$in": session_ids}}]}
        data[name] = await repository.db[name].find(query).to_list(None)
    folder = Path(__file__).resolve().parents[2] / ".local" / "seed-backups"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / (utcnow().strftime("%Y%m%dT%H%M%S%f") + ".json")
    path.write_text(json_util.dumps(data, json_options=json_util.RELAXED_JSON_OPTIONS.with_options(uuid_representation=UuidRepresentation.STANDARD)), encoding="utf-8")
    return str(path)


async def seed():
    fixtures = await build_cohort()  # Build completely before touching the database.
    repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
    await repository.initialize()
    try:
        lifecycle = await repository.get_study_lifecycle(settings.study_protocol_version)
        if lifecycle and (lifecycle.dataset_frozen_at or lifecycle.freeze_token):
            raise ValueError("Cannot replace fixtures in a frozen study database")
        backup = await backup_seeded(repository)
        removed = await clear_seeded(repository)
        users = await fixtures.list_users()
        count = 0
        for user in users:
            await repository.create_user(user)
            for session in await fixtures.list_sessions(user.id):
                await repository.save_session(session)
                count += 1
            for record in await fixtures.list_study_records(user.id):
                await repository.save_study_record(record)
        return {"synthetic_users": len(users), "sessions": count, "backup": backup, "removed_previous": removed}
    finally:
        await repository.client.close()


async def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "clear"), nargs="?", default="seed")
    args = parser.parse_args()
    if args.command == "seed":
        print(await seed())
    else:
        repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
        await repository.initialize()
        try:
            print({"backup": await backup_seeded(repository), "removed": await clear_seeded(repository)})
        finally:
            await repository.client.close()


if __name__ == "__main__":
    asyncio.run(main())
