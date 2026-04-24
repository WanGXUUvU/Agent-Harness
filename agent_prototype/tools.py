def echo_tool(text: str) -> str:
    # 这是本地真正执行的工具逻辑。
    # 模型只会返回 tool_calls，真正的函数执行发生在这里。
    return f"tool received:{text}"



#工具说明书

ECHO_TOOL_SCHEMA={
    "type":"function",
    "function":{
        "name":"echo_tool",
        "description":"Echo the input text back to the caller",
        #参数定义，告诉模型这个工具要收到什么输入
        "parameters":{
            "type":"object",
            "properties":{
                "text":{
                    "type":"string",
                    "description":"Text to echo back.",
                }
            },
            "required":["text"],
            "additionalProperties":False,
        },
    },
}


TOOLS=[ECHO_TOOL_SCHEMA]