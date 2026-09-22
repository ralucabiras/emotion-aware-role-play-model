"""Seed clearly labelled, deterministic synthetic pilot and session data."""
import argparse
import asyncio
from datetime import timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

from app.core.config import settings
from app.models.domain import (
    ConversationTurn,
    Difficulty,
    EmotionLabel,
    EmotionState,
    FeedbackMetric,
    PracticeGoal,
    ResearchEvent,
    Role,
    RolePlayState,
    RolePlayStatus,
    Session,
    SessionFeedback,
    StudyConsentRecord,
    StudyQuestionnaire,
    StudyRecord,
    TurnEvidence,
    User,
    utcnow,
)
from app.repositories.mongo import MongoRepository
from app.services.auth_service import password_hash
from app.services.roleplay_service import SCENARIOS

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
SCENARIO_TURNS = {
    "workload": ["Could we review my priorities?", "I need the internal report moved to next week because the client deadline is Friday."],
    "boundary": ["I cannot take this on this week.", "I understand it matters, but my answer is still no."],
    "relationship": ["I feel disconnected when we do not have time together.", "I would like one evening each week without phones so we can talk."],
    "deadline": ["The current date puts quality at risk.", "I would like to deliver on Tuesday, or reduce the scope for Friday."],
}


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


def build_session(user: User, scenario_id: str, index: int, completed: bool = True) -> tuple[Session, StudyRecord]:
    now = utcnow() - timedelta(days=index + 1)
    session_id = stable_uuid(f"{user.email}/{scenario_id}/{index}")
    messages = SCENARIO_TURNS[scenario_id]
    turns = [ConversationTurn(role=Role.ASSISTANT, content=SCENARIOS[scenario_id].opening_line, created_at=now)]
    for turn_index, message in enumerate(messages, 1):
        turns.extend([
            ConversationTurn(role=Role.USER, content=message, created_at=now + timedelta(minutes=turn_index * 2)),
            ConversationTurn(role=Role.ASSISTANT, content="Thank you. That gives me a clear understanding of what you need.", created_at=now + timedelta(minutes=turn_index * 2 + 1)),
        ])
    score = min(0.94, 0.58 + (index % 5) * 0.08)
    metrics = [
        FeedbackMetric(name="clarity", score=score, evidence_turns=[1, 2]),
        FeedbackMetric(name="specificity", score=max(0.45, score - 0.07), evidence_turns=[2]),
        FeedbackMetric(name="boundary_maintenance", score=max(0.4, score - 0.12), evidence_turns=[2]),
    ]
    state = RolePlayState(
        scenario_id=scenario_id,
        scenario=SCENARIOS[scenario_id],
        status=RolePlayStatus.COMPLETED if completed else RolePlayStatus.PAUSED,
        difficulty_level=[Difficulty.BEGINNER, Difficulty.INTERMEDIATE, Difficulty.DIFFICULT][index % 3],
        turn=2,
        success_progress=1 if completed else 0.66,
        completion_reason="success" if completed else None,
        started_at=now,
        completed_at=now + timedelta(minutes=8) if completed else None,
        evidence=[
            TurnEvidence(turn=1, concrete_request=True, i_statement=True, arousal=0.45),
            TurnEvidence(turn=2, concrete_request=True, maintained_boundary=True, specific_detail=True, i_statement=True, arousal=0.36),
        ],
    )
    feedback = SessionFeedback(
        session_id=session_id,
        scenario_id=scenario_id,
        metrics=metrics,
        observed=["Used concrete request language.", "Included a specific detail."],
        strengths=["The request was clear and actionable."],
        suggestions=["State the boundary earlier when resistance appears."],
        generation_source="template",
        created_at=now + timedelta(minutes=9),
    ) if completed else None
    questionnaires = {
        "pre": StudyQuestionnaire(phase="pre", confidence=3 + index % 2, anxiety=5, submitted_at=now),
        "post": StudyQuestionnaire(phase="post", confidence=5 + index % 2, realism=5 + index % 3, usefulness=6, submitted_at=now + timedelta(minutes=10)),
    } if completed else {"pre": StudyQuestionnaire(phase="pre", confidence=3, anxiety=5, submitted_at=now)}
    natural_titles = {"workload": "Preparing for my manager meeting", "boundary": "Saying no without guilt", "relationship": "Talking about quality time", "deadline": "Deadline conversation"}
    session = Session(
        id=session_id, user_id=user.id, title=natural_titles[scenario_id], created_at=now,
        updated_at=now + timedelta(minutes=10), expires_at=utcnow() + timedelta(days=30), turns=turns,
        emotion_state=EmotionState(dominant_emotion=EmotionLabel.ANXIETY, arousal=0.36, confidence=0.71),
        roleplay=state, feedback=feedback, takeaway="Lead with the request, then explain the constraint.",
        questionnaires=questionnaires,
        research_events=[ResearchEvent(name="synthetic_seed", created_at=now), ResearchEvent(name="roleplay_started", created_at=now), ResearchEvent(name="roleplay_completed" if completed else "roleplay_paused", created_at=now + timedelta(minutes=8))],
    )
    record = StudyRecord(
        id=stable_uuid(f"record/{session_id}"), user_id=user.id, participant_id=user.participant_id, session_id=session.id,
        consent_version=settings.study_consent_version, protocol_version=settings.study_protocol_version,
        enrolled_at=user.pilot_enrolled_at or now, session_created_at=now, last_activity_at=session.updated_at,
        retention_expires_at=utcnow() + timedelta(days=settings.study_record_retention_days), turn_count=len(turns),
        scenario_id=scenario_id, difficulty=state.difficulty_level, completion_reason=state.completion_reason,
        feedback_metrics=metrics if completed else [], feedback_generation_source="template" if completed else None,
        questionnaires=questionnaires, events=session.research_events, created_at=now, updated_at=session.updated_at,
    )
    return session, record


async def seed(owner_email: str | None) -> dict[str, int | str]:
    repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
    await repository.initialize()
    removed = await clear_seeded(repository)
    shared_hash = password_hash.hash(PASSWORD)
    users: list[User] = []
    for index, (first_name, last_name, email, city) in enumerate(PROFILES):
        enrolled = utcnow() - timedelta(days=35 - index * 2)
        user = User(
            id=stable_uuid(f"user/{index}"), participant_id=stable_uuid(f"participant/{index}"),
            email=email, password_hash=shared_hash,
            consented_at=enrolled, consent_version=settings.research_consent_version, first_name=first_name,
            last_name=last_name, preferred_name=first_name, country=f"Romania · {city}", timezone="Europe/Bucharest",
            email_verified_at=enrolled, onboarding_completed_at=enrolled, onboarding_version=settings.onboarding_version,
            practice_goals=[PracticeGoal.CLEAR_REQUESTS, PracticeGoal.ASSERTIVENESS], pilot_enrolled_at=enrolled,
            study_consent=StudyConsentRecord(version=settings.study_consent_version, protocol_version=settings.study_protocol_version, accepted_at=enrolled),
            study_data_quality_notes="Complete responses; no quality concerns.", created_at=enrolled,
        )
        await repository.create_user(user)
        users.append(user)
    owner = await repository.get_user_by_email(owner_email) if owner_email else None
    if not owner:
        real_user = await repository.db.users.find_one(
            {"id": {"$nin": [user.id for user in users]}}, sort=[("created_at", -1)]
        )
        owner = User.model_validate(real_user) if real_user else None
    sessions = records = 0
    scenario_ids = list(SCENARIO_TURNS)
    for index, user in enumerate(users):
        for offset in range(2):
            session, record = build_session(user, scenario_ids[(index + offset) % len(scenario_ids)], index * 2 + offset, completed=not (index == 9 and offset == 1))
            await repository.save_session(session)
            await repository.save_study_record(record)
            sessions += 1
            records += 1
    if owner:
        for index, scenario_id in enumerate(("workload", "boundary", "relationship")):
            session, _ = build_session(owner, scenario_id, index)
            await repository.save_session(session)
            sessions += 1
    await repository.client.close()
    return {"synthetic_users": len(users), "sessions": sessions, "study_records": records, "owner_history_seeded": bool(owner), "removed_previous": sum(removed.values())}


async def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("seed", "clear"), nargs="?", default="seed")
    parser.add_argument("--owner-email", help="Also add three labelled synthetic sessions to this existing account")
    args = parser.parse_args()
    repository = MongoRepository(settings.mongodb_uri, settings.mongodb_database)
    if args.command == "clear":
        await repository.initialize()
        print(await clear_seeded(repository))
        await repository.client.close()
        return
    owner_email = args.owner_email or next((item.strip() for item in settings.researcher_emails.split(",") if item.strip()), None)
    print(await seed(owner_email))


if __name__ == "__main__":
    asyncio.run(main())
