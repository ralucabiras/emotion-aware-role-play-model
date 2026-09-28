"""Copy-on-write rehearsal forks; no source writes or regenerated explanations."""
import hashlib
import json
from uuid import uuid5

from app.models.domain import BranchLineage, ResearchEvent, Role, RolePlayStatus, Session, utcnow
from app.repositories.mongo import ConcurrentSessionUpdateError
from app.services import scenario_dialogue, workload_dialogue


def rehearsal_turns(session):
    state = session.roleplay
    if not state:
        return []
    end = state.measurement_ended_at or state.completed_at
    if state.completed_at and not state.measurement_ended_at:
        for previous, turn in zip(session.turns, session.turns[1:], strict=False):
            if turn.role == Role.ASSISTANT and previous.role == Role.USER and previous.created_at <= state.completed_at:
                end = max(end, turn.created_at)
    context = set(session.branch.copied_turn_ids) if session.branch else set()
    return [turn for turn in session.turns if turn.id in context or
            (turn.created_at >= state.started_at and (end is None or turn.created_at <= end))]


def source_digest(session):
    data = {"turns": [turn.model_dump(mode="json") for turn in rehearsal_turns(session)],
            "roleplay": session.roleplay.model_dump(mode="json")}
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def supported(state):
    if not state or not state.dialogue or not state.scenario or state.required_task_id or state.attempt_purpose == "required":
        return False
    if state.policy_version == workload_dialogue.VERSION:
        return state.scenario_id == "workload" and state.scenario_version == state.scoring_version == workload_dialogue.VERSION
    definition = scenario_dialogue.DEFINITIONS.get(state.scenario_id)
    return bool(definition and state.policy_version == scenario_dialogue.VERSION and
                state.scenario_version == state.scoring_version == definition.version and
                state.character_profile in scenario_dialogue.PROFILES)


async def create_branch(service, session_id, user_id, turn_id, expected_version, request_id):
    # A repeated request maps to one child even across workers/restarts. New
    # request IDs deliberately create independent alternatives.
    child_id = uuid5(user_id, f"rehearsal-branch:{request_id}")
    existing = await service.repository.get_session(child_id, user_id)
    if existing:
        if (existing.branch and existing.branch.parent_session_id == session_id and
                existing.branch.branch_point_turn_id == turn_id and existing.branch.parent_version == expected_version):
            return existing
        raise ValueError("This branch request was already used. Reload before trying again.")
    parent = (await service.get_session(session_id, user_id)).model_copy(deep=True)
    if parent.version != expected_version:
        raise ValueError("The original changed. Reload it before creating an alternative.")
    state = parent.roleplay
    if not supported(state) or state.status not in {RolePlayStatus.COMPLETED, RolePlayStatus.INTERRUPTED}:
        raise ValueError("This rehearsal cannot be branched with its saved policy. Start a fresh attempt instead.")
    if parent.branch and turn_id in parent.branch.copied_turn_ids:
        raise ValueError("Shared context cannot be changed in this branch. Choose one of its new responses.")
    decisions = state.decisions
    decision_index = next((i for i, item in enumerate(decisions) if item.user_turn_id == turn_id), None)
    if decision_index is None:
        raise ValueError("No saved pre-turn decision exists here. Start a fresh attempt instead.")
    decision = decisions[decision_index]
    snapshot = decision.before
    turns = rehearsal_turns(parent)
    index = next((i for i, turn in enumerate(turns) if turn.id == turn_id), None)
    if (snapshot.status != RolePlayStatus.ACTIVE or index is None or turns[index].role != Role.USER or
            index + 1 >= len(turns) or turns[index + 1].id != decision.assistant_turn_id or
            (decision.policy_version, decision.scenario_version, decision.scoring_version, decision.character_profile) !=
            (state.policy_version, state.scenario_version, state.scoring_version, state.character_profile)):
        raise ValueError("The saved branch point is incomplete or unsupported. Start a fresh attempt instead.")
    copied = turns[:index]
    copied_ids = {turn.id for turn in copied}
    evidence = [item for item in state.evidence if item.turn <= snapshot.turn and item.conversation_turn_id in copied_ids]
    prior = decisions[:decision_index]
    if len(evidence) != snapshot.turn or any(item.user_turn_id not in copied_ids or item.assistant_turn_id not in copied_ids for item in prior):
        raise ValueError("The saved context is incomplete. Start a fresh attempt instead.")
    now = utcnow()
    state.dialogue = snapshot.dialogue.model_copy(deep=True)
    state.status, state.completion_reason = snapshot.status, snapshot.completion_reason
    state.turn, state.success_progress = snapshot.turn, snapshot.success_progress
    state.difficulty, state.cooperation = snapshot.difficulty, snapshot.cooperation
    state.evidence, state.decisions = evidence, prior
    state.started_at, state.completed_at, state.measurement_ended_at = now, None, None
    state.attempt_purpose, state.required_task_id = "retry", None
    # Read the digest from the unmodified stored source, not the restored state.
    current = await service.get_session(session_id, user_id)
    if current.version != expected_version:
        raise ValueError("The original changed. Reload it before creating an alternative.")
    lineage = BranchLineage(parent_session_id=session_id, parent_version=expected_version,
        branch_point_turn_id=turn_id, branch_group_id=parent.branch.branch_group_id if parent.branch else parent.id,
        request_id=request_id, before=snapshot.model_copy(deep=True), copied_turn_ids=[turn.id for turn in copied],
        copied_evidence_turns=[item.turn for item in evidence], source_digest=source_digest(current), created_at=now)
    child = Session(id=child_id, user_id=user_id, title=f"Alternative: {parent.title}"[:80], branch=lineage,
        turns=copied, roleplay=state, emotion_state=snapshot.emotion_state.model_copy(deep=True),
        research_events=[ResearchEvent(name="branch_created", properties={"copied_turn_count": len(copied)})])
    try:
        await service.save(child)
    except ConcurrentSessionUpdateError:
        # A concurrent duplicate may have won the unique session-ID insert.
        winner = await service.repository.get_session(child_id, user_id)
        if winner and winner.branch == lineage:
            return winner
        if winner and winner.branch and (winner.branch.parent_session_id, winner.branch.branch_point_turn_id,
                                         winner.branch.parent_version) == (session_id, turn_id, expected_version):
            return winner
        raise
    return child


def continuation(session, copied_ids):
    turns = [turn for turn in rehearsal_turns(session) if turn.id not in copied_ids]
    ids = {turn.id for turn in turns}
    return {"session_id": session.id, "title": session.title, "status": session.roleplay.status,
            "outcome": session.roleplay.dialogue.outcome, "agreement": session.roleplay.dialogue.final_agreement,
            "completion_reason": session.roleplay.completion_reason, "turns": turns,
            "decisions": [item for item in session.roleplay.decisions if item.user_turn_id in ids],
            "evidence": [item for item in session.roleplay.evidence if item.conversation_turn_id in ids]}


async def compare_branch(service, session_id, user_id):
    child = await service.get_session(session_id, user_id)
    if not child.branch:
        raise ValueError("This session is not an alternative rehearsal.")
    parent = await service.repository.get_session(child.branch.parent_session_id, user_id)
    reason = None
    if parent is None:
        reason = "The original was deleted or expired. Your copied context and alternative are still available."
    elif not parent.roleplay or source_digest(parent) != child.branch.source_digest:
        reason = "The original rehearsal changed after branching, so its continuation is no longer comparable."
    copied_ids = set(child.branch.copied_turn_ids)
    return {"shared_context": [turn for turn in child.turns if turn.id in copied_ids],
            "original": continuation(parent, copied_ids) if reason is None else None,
            "alternative": continuation(child, copied_ids), "unavailable_reason": reason,
            "branch": child.branch}
