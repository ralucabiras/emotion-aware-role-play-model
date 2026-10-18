"""Local usage fixtures obey the same persistence and measurement rules as real use."""
import pytest

from app.services.roleplay_service import RolePlayService
from app.services.study_tasks import is_completed_protocol_task, select_required_attempts
from scripts.seed_mock_data import build_cohort


@pytest.mark.asyncio
async def test_synthetic_cohort_is_consistent_and_covers_incomplete_paths():
    repo = await build_cohort()
    users = await repo.list_users()
    assert len(users) == 22
    cohort = [user for user in users if user.pilot_enrolled_at]
    active_cohort = [user for user in cohort if not user.study_withdrawal and not user.study_excluded_at]
    assert len(cohort) == 17
    assert len(active_cohort) == 15
    completed = []
    turn_counts, usefulness, changes = set(), set(), set()
    for user in active_cohort:
        assert user.study_eligibility.confirmed_at == user.pilot_enrolled_at
        records = await repo.list_study_records(user.id)
        selected = select_required_attempts(records)
        completed.append(sum(is_completed_protocol_task(r) for r in selected.values()))
        ordered = sorted(selected.values(), key=lambda r: r.roleplay_started_at)
        assert [r.scenario_id for r in ordered] == ["workload", "boundary", "relationship"][:len(ordered)]
        for record in records:
            session = await repo.get_session(record.session_id, user.id)
            assert not session.title.startswith("[")
            assert all(e.name != "synthetic_seed" for e in record.events)
            assert user.pilot_enrolled_at <= session.created_at <= record.roleplay_started_at
            assert record.turn_count == len(session.turns)
            assert sum(record.generation_source_counts.values()) == sum(t.role == "assistant" for t in session.turns)
            assert all(e.conversation_turn_id in {t.id for t in session.turns} for e in session.roleplay.evidence)
            turn_counts.add(record.turn_count)
            if session.feedback:
                assert session.feedback.metrics == RolePlayService().feedback(session.roleplay).metrics
                assert record.roleplay_completed_at >= record.roleplay_started_at
                if record.attempt_purpose == "required":
                    assert record.scoring_version == "affectlab-required-lexical-v1.1"
            if "post" in session.questionnaires:
                post = session.questionnaires["post"]
                assert post.submitted_at >= record.roleplay_completed_at
                usefulness.add(post.usefulness)
                if "pre" in session.questionnaires:
                    changes.add(post.confidence - session.questionnaires["pre"].confidence)
            if "pre" in session.questionnaires:
                assert session.questionnaires["pre"].submitted_at <= record.roleplay_started_at
            if record.attempt_purpose == "retry":
                assert record.session_id != selected[record.required_task_id].session_id
    assert sorted(completed) == [0, 1, 2] + [3] * 12
    assert len(turn_counts) >= 3
    assert len(usefulness) >= 3
    assert min(changes) < 0 < max(changes)
