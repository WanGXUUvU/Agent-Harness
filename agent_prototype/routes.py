from fastapi import APIRouter
from .agent import Agent
from .schemas import AgentInput,AgentOutput

router=APIRouter()
agent=Agent()

@router.post("/run",response_model=AgentOutput)
def run_agent_api(agent_input:AgentInput):
    return agent.run(agent_input)