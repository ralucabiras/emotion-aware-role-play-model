from uuid import UUID

from fastapi import APIRouter, HTTPException, Response, status

from app.models.domain import ConversationTurn, Role
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    CreateSessionResponse,
    SessionResponse,
    StartRolePlayRequest,
    StartRolePlayResponse,
)
from app.services.conversation_service import SessionNotFoundError, conversation_service
from app.services.roleplay_service import SCENARIOS

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/sessions", response_model=CreateSessionResponse, status_code=status.HTTP_201_CREATED)
def create_session() -> CreateSessionResponse:
    session = conversation_service.create_session()
    return CreateSessionResponse(session_id=session.id, emotion_state=session.emotion_state)


@router.get("/sessions/{session_id}", response_model=SessionResponse)
def get_session(session_id: UUID) -> SessionResponse:
    try:
        session = conversation_service.get_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    return SessionResponse(
        session_id=session.id,
        turns=session.turns,
        emotion_state=session.emotion_state,
        roleplay=session.roleplay,
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: UUID) -> Response:
    try:
        conversation_service.delete_session(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    try:
        turn, decision = await conversation_service.chat(request.session_id, request.message)
        session = conversation_service.get_session(request.session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    return ChatResponse(turn=turn, decision=decision, roleplay=session.roleplay)


@router.get("/roleplay/scenarios")
def list_scenarios():
    return list(SCENARIOS.values())


@router.post("/sessions/{session_id}/roleplay", response_model=StartRolePlayResponse)
def start_roleplay(session_id: UUID, request: StartRolePlayRequest) -> StartRolePlayResponse:
    try:
        session = conversation_service.get_session(session_id)
        state, scenario = conversation_service.roleplays.start(request.scenario_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found") from None
    except KeyError:
        raise HTTPException(status_code=404, detail="Scenario not found") from None
    session.roleplay = state
    turn = ConversationTurn(role=Role.ASSISTANT, content=scenario.opening_line)
    session.turns.append(turn)
    return StartRolePlayResponse(state=state, scenario=scenario, opening_turn=turn)
