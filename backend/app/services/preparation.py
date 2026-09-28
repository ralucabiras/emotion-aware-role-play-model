"""Bounded, offline preparation templates; never assertions about another person."""
from app.models.domain import ActionCard, Difficulty, PreparationDetails, Role, RolePlayScenario, utcnow
from app.schemas.chat import CustomScenarioRequest
from app.services.branching import rehearsal_turns

SKILLS = {"clear request": "concrete_request", "specific detail": "specific_detail",
          "boundary maintenance": "maintained_boundary", "I-statements": "i_statement",
          "non-blaming language": "no_blame"}


def prepare_brief(request):
    return CustomScenarioRequest(title=f"Talk with {request.who}"[:80], character=request.who,
        situation=request.happened, user_objective=request.desired_outcome,
        opening_line="You wanted to talk. What would you like to change?",
        skills=["clear request", "specific detail"],
        preparation=PreparationDetails(difficult_part=request.difficult_part,
            likely_objection="I may need more detail before deciding. What are you asking me to do?"))


def custom_scenario(request, scenario_id):
    skills = list(dict.fromkeys(request.skills))
    if any(skill not in SKILLS for skill in skills):
        raise ValueError("Unsupported practice skill")
    return RolePlayScenario(id=scenario_id, title=" ".join(request.title.split()),
        character=" ".join(request.character.split()), situation=request.situation.strip(),
        user_objective=request.user_objective.strip(), opening_line=request.opening_line.strip(),
        preparation=request.preparation.model_copy(deep=True) if request.preparation else None,
        expected_skills=skills,
        difficulty_behaviors={Difficulty.BEGINNER: "Supportive and curious", Difficulty.INTERMEDIATE: "Questions details and offers mild resistance", Difficulty.DIFFICULT: "Pushes back firmly while remaining respectful"},
        success_conditions=[SKILLS[skill] for skill in skills], max_turns=8)


def action_card_draft(session):
    state = session.roleplay
    if not state or state.status not in {"completed", "interrupted"}:
        raise ValueError("Finish the rehearsal before preparing an action card.")
    if session.action_card:
        return session.action_card.model_copy(deep=True)
    copied = set(session.branch.copied_turn_ids) if session.branch else set()
    users = [turn for turn in rehearsal_turns(session) if turn.role == Role.USER and turn.id not in copied]
    # Do not reuse a crisis utterance as suggested real-world wording.
    if state.completion_reason == "safety_interruption" or not (state.measurement_ended_at or state.completed_at):
        users = []
    boundary_ids = {item.conversation_turn_id for item in state.evidence if item.maintained_boundary}
    boundary = next((turn for turn in reversed(users) if turn.id in boundary_ids), None)
    opening = users[0] if users else None
    return ActionCard(opening_sentence=opening.content[:500] if opening else "Could we find a good time to talk about something important to me?",
        main_request=(state.scenario.user_objective if state.scenario else "State one specific change you would like to ask for.")[:500],
        boundary_or_fallback=boundary.content[:500] if boundary else "If we cannot agree now, I can pause and suggest another time to talk.",
        reminder="Make one clear request, listen to the response, and decide what you are comfortable with.",
        source_turn_ids=list(dict.fromkeys(turn.id for turn in [opening, boundary] if turn)))


async def save_action_card(service, session_id, user_id, request):
    session = (await service.get_session(session_id, user_id)).model_copy(deep=True)
    if session.version != request.expected_version:
        raise ValueError("This session changed. Refresh the saved version before saving your card.")
    draft = action_card_draft(session)
    session.action_card = draft.model_copy(update={**request.model_dump(exclude={"expected_version"}),
                                                  "source": "user-edited", "updated_at": utcnow()})
    # No scoring, questionnaire, research event or measurement-boundary changes.
    await service.save(session)
    return session
