"""Versioned, text-free tabular data for live and immutable research exports."""
import csv
import io
import json
from collections import Counter

from app.core.config import settings
from app.services.study_tasks import is_completed_protocol_task, select_required_attempts

CSV_SCHEMA_VERSION = "affectlab-frozen-dataset-v3"
CSV_FIELDS = [
    "schema_version", "row_type", "protocol_version", "participant_id", "enrolled_at",
    "consent_version", "consented_at", "eligibility_version", "eligibility_confirmed_at",
    "session_id", "created_at", "updated_at", "turn_count", "scenario_id", "difficulty",
    "attempt_purpose", "required_task_id", "primary_attempt", "primary_task_complete",
    "completion_reason", "roleplay_started_at", "roleplay_completed_at",
    "pre_confidence", "pre_anxiety", "pre_submitted_at",
    "post_confidence", "post_realism", "post_usefulness", "post_submitted_at",
    "feedback_metrics_json", "feedback_generation_source",
    "generation_source_counts_json", "fallback_reason_counts_json", "event_counts_json",
]


def timestamp(value):
    return value.isoformat() if value else ""


def json_cell(value):
    return "" if value is None else json.dumps(value, sort_keys=True, separators=(",", ":"))


async def export_research_rows(repository, users, deidentified=False):
    users = sorted(users, key=lambda user: (user.pilot_enrolled_at, str(user.participant_id)))
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=CSV_FIELDS)
    writer.writeheader()
    row_count = 0
    for participant_index, participant in enumerate(users, 1):
        participant_id = f"P{participant_index:04d}" if deidentified else str(participant.participant_id)
        common = {
            "schema_version": CSV_SCHEMA_VERSION,
            "protocol_version": settings.study_protocol_version,
            "participant_id": participant_id,
            "enrolled_at": timestamp(participant.pilot_enrolled_at),
            "consent_version": participant.study_consent.version,
            "consented_at": timestamp(participant.study_consent.accepted_at),
            "eligibility_version": participant.study_eligibility.version,
            "eligibility_confirmed_at": timestamp(participant.study_eligibility.confirmed_at),
        }
        records = [record for record in await repository.list_study_records(participant.id)
                   if record.protocol_version == settings.study_protocol_version]
        primary_ids = {record.session_id for record in select_required_attempts(records).values()}
        records.sort(key=lambda record: (record.session_created_at, str(record.session_id)))
        if not records:
            writer.writerow({**common, "row_type": "participant"})
            row_count += 1
        for session_index, record in enumerate(records, 1):
            pre, post = record.questionnaires.get("pre"), record.questionnaires.get("post")
            writer.writerow({
                **common,
                "row_type": "session",
                "consent_version": record.consent_version,
                "session_id": f"{participant_id}-S{session_index:03d}" if deidentified else str(record.session_id),
                "created_at": timestamp(record.session_created_at),
                "updated_at": timestamp(record.last_activity_at),
                "turn_count": record.turn_count,
                "scenario_id": record.scenario_id or "",
                "difficulty": record.difficulty.value if record.difficulty else "",
                "attempt_purpose": record.attempt_purpose,
                "required_task_id": record.required_task_id or "",
                "primary_attempt": record.session_id in primary_ids,
                "primary_task_complete": record.session_id in primary_ids and is_completed_protocol_task(record),
                "completion_reason": record.completion_reason or "",
                "roleplay_started_at": timestamp(record.roleplay_started_at),
                "roleplay_completed_at": timestamp(record.roleplay_completed_at),
                "pre_confidence": pre.confidence if pre else "",
                "pre_anxiety": pre.anxiety if pre else "",
                "pre_submitted_at": timestamp(pre.submitted_at) if pre else "",
                "post_confidence": post.confidence if post else "",
                "post_realism": post.realism if post else "",
                "post_usefulness": post.usefulness if post else "",
                "post_submitted_at": timestamp(post.submitted_at) if post else "",
                "feedback_metrics_json": json_cell([metric.model_dump(mode="json") for metric in record.feedback_metrics]),
                "feedback_generation_source": record.feedback_generation_source or "",
                "generation_source_counts_json": json_cell(record.generation_source_counts),
                "fallback_reason_counts_json": json_cell(record.fallback_reason_counts),
                # Event properties can contain custom wording; only export counts.
                "event_counts_json": json_cell(dict(Counter(event.name for event in record.events))),
            })
            row_count += 1
    return output.getvalue(), row_count, len(users)
