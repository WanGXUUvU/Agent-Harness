from .schemas import AgentInput,AgentState,AgentOutput,ChatMessage
from .llm_client import call_llm

class Agent:
    def __init__(self):
        self.state=AgentState()
        
    def run(self,agent_input:AgentInput) -> AgentOutput:
        self.state.messages.append(ChatMessage(role="user",content=agent_input.user_input))
        self.state.step += 1
        

        messages=[ChatMessage(role="system",content="You are a helpful assistant.")]+self.state.messages

        reply = call_llm([message.model_dump() for message in messages])

        self.state.messages.append(
            ChatMessage(role="assistant",content=reply)
        )

        return AgentOutput(reply=reply,state=self.state)