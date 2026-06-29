"""放 prompt 共用的小辅助函数。"""


def wrap_section(tag: str, content: str) -> str:
    """用统一的 XML 标签包裹内容。"""
    return f"<{tag}>\n{content.strip()}\n</{tag}>"
