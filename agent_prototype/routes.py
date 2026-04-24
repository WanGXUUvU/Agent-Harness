from fastapi import APIRouter

from .agent import Agent
from .schemas import AgentInput, AgentOutput, AgentState, ResetInput


router = APIRouter()
session_store: dict[str, AgentState] = {}


@router.post("/run", response_model=AgentOutput)
def run_agent_api(agent_input: AgentInput):
    state = session_store.get(agent_input.session_id) or AgentState()
    agent = Agent(state=state)
    output = agent.run(agent_input)
    session_store[agent_input.session_id] = output.state
    return output


@router.post("/reset")
def reset_session(payload: ResetInput):
    session_store.pop(payload.session_id, None)
    return {"ok": True}
