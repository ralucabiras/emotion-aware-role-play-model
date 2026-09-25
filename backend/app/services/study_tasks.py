"""One selection rule for required study attempts, monitoring, and exports."""
from app.core.config import settings
from app.models.domain import Difficulty, StudyRecord

PROTOCOL_TASK_ORDER = ("workload", "boundary", "relationship")
PROTOCOL_REQUIRED_SCENARIOS = set(PROTOCOL_TASK_ORDER)
QUALIFYING_COMPLETION_REASONS = {"success", "maximum_turns", "user_finished"}


def is_completed_rehearsal(record: StudyRecord) -> bool:
    return bool(record.scenario_id and record.completion_reason in QUALIFYING_COMPLETION_REASONS)


def has_complete_post_questionnaire(record: StudyRecord) -> bool:
    post = record.questionnaires.get("post")
    return bool(
        post and post.phase == "post"
        and all(value is not None and 1 <= value <= 7 for value in (
            post.confidence, post.realism, post.usefulness,
        ))
    )


def is_completed_protocol_task(record: StudyRecord) -> bool:
    return bool(record.attempt_purpose == "required"
                and record.required_task_id == record.scenario_id
                and record.scenario_id in PROTOCOL_REQUIRED_SCENARIOS
                and record.difficulty == Difficulty.INTERMEDIATE
                and is_completed_rehearsal(record) and has_complete_post_questionnaire(record))



def select_required_attempts(records):
    """First explicitly required attempt per task; never replace it with practice.

    Stable ties use session UUID. The caller supplies one participant's records.
    Invalid and unclassified legacy records are not silently promoted.
    """
    selected = {}
    candidates = [record for record in records
                  if record.protocol_version == settings.study_protocol_version
                  and record.attempt_purpose == "required"
                  and record.required_task_id in PROTOCOL_REQUIRED_SCENARIOS
                  and record.scenario_id == record.required_task_id
                  and record.difficulty == Difficulty.INTERMEDIATE]
    for record in sorted(candidates, key=lambda item: (item.roleplay_started_at or item.session_created_at, str(item.session_id))):
        selected.setdefault(record.required_task_id, record)
    return selected
