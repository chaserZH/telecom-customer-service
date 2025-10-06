"""
Action数据类定义
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from enum import Enum


class ActionType(str, Enum):
    """系统动作类型"""
    REQUEST = "REQUEST"  # 请求用户提供信息
    INFORM = "INFORM"  # 告知用户信息
    CONFIRM = "CONFIRM"  # 确认用户意图
    RECOMMEND = "RECOMMEND"  # 主动推荐
    EXECUTE = "EXECUTE"  # 执行业务操作
    CLARIFY = "CLARIFY"  # 澄清歧义
    APOLOGIZE = "APOLOGIZE"  # 致歉
    CLOSE = "CLOSE"  # 结束对话


@dataclass
class Action:
    """系统动作"""
    action_type: ActionType
    intent: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    requires_confirmation: bool = False

    # NLG相关
    template_key: Optional[str] = None
    use_llm: bool = False

    # 元数据
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转为字典"""
        return {
            "action_type": self.action_type.value if isinstance(self.action_type, ActionType) else self.action_type,
            "intent": self.intent,
            "parameters": self.parameters,
            "priority": self.priority,
            "requires_confirmation": self.requires_confirmation,
            "template_key": self.template_key,
            "use_llm": self.use_llm,
            "metadata": self.metadata
        }
