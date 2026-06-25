"""提示词层类型定义。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class PromptSection:
    """一段可独立装配的 system prompt section。"""

    key: str
    content: str
