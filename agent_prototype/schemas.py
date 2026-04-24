from pydantic import BaseModel, Field
from typing import List,Literal,Optional


class ToolCallFunction(BaseModel):
    name:str
    arguments:str

class ToolCall(BaseModel):
    id:str
    type:Literal["function"]="function"
    function:ToolCallFunction

class ChatMessage(BaseModel):
    role:Literal["system","user","assistant","tool"]
    content:Optional[str]=None
    tool_calls:Optional[list[ToolCall]]=None
    tool_call_id:Optional[str]=None
#单词运行请求
class AgentInput(BaseModel):
    session_id:str=Field(min_length=1) #会话id，隔离会话
    user_input:str =Field(min_length=1)
#重置请求
class ResetInput(BaseModel):
    session_id:str=Field(min_length=1)

class AgentState(BaseModel):
    messages:List[ChatMessage]=Field(default_factory=list)
    step:int=0

class AgentEvent(BaseModel):
    type:Literal["assistant_tool_call","tool_result","final_answer"]
    content:Optional[str]=None
    tool_name:Optional[str]=None
    tool_call_id:Optional[str]=None

class AgentOutput(BaseModel):
    reply:str
    state:AgentState
    events: List[AgentEvent]
