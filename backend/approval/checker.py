"""审批策略判断。"""

from backend.security.policy.types import ApprovalPolicy
from backend.tools.types import RiskLevel


def needs_approval(policy: ApprovalPolicy, risk: RiskLevel) -> bool:
    """判断工具调用是否需要人工审批。"""
    if policy == ApprovalPolicy.NEVER:
        return False
    if policy == ApprovalPolicy.UNTRUSTED:
        return risk != RiskLevel.SAFE
    if policy == ApprovalPolicy.ON_REQUEST:
        return risk == RiskLevel.DANGER
    return False
