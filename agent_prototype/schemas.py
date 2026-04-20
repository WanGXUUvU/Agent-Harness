from pydantic import BaseModel, Field
from typing import List,Literal
class ChatMessage(BaseModel):
    role:Literal["system","user","assistant"]
    content:str
    
class AgentInput(BaseModel):
    user_input:str =Field(min_length=1)

class AgentState(BaseModel):
    messages:List[ChatMessage]=Field(default_factory=list)
    step:int=0

class AgentOutput(BaseModel):
    reply:str
    state:AgentState

