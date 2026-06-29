"""放 SSE 格式化相关辅助函数。"""

import json


def _sse_frame(frame_type: str, data: dict) -> str:
    """序列化数据帧为标准的 SSE (Server-Sent Events) 文本帧格式。"""
    payload = {
        "type": frame_type,
        "data": data,
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def build_reply_preview(reply: str, max_len: int = 120) -> str:
    """生成用于会话列表的单行回复预览，默认截断到 120 字符。"""
    text = " ".join(reply.split())
    return text[:max_len]
