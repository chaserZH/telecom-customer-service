"""
对话状态数据结构
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional, Dict, Any, List


@dataclass
class DialogTurn:
    """对话轮次"""
    turn_id: int
    role: str  # 'user' or 'assistant'
    content: str
    intent: Optional[str] = None
    entities: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """转为字典"""
        result = asdict(self)
        result['timestamp'] = self.timestamp.isoformat()
        return result

    @classmethod
    def from_dict(cls, data: Dict) -> 'DialogTurn':
        """从字典创建"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


@dataclass
class DialogState:
    """对话状态"""
    session_id: str
    user_phone: Optional[str] = None
    user_name: Optional[str] = None
    current_intent: Optional[str] = None
    previous_intent: Optional[str] = None

    # 槽位值
    slots: Dict[str, Any] = field(default_factory=dict)

    # 对话历史（最近20轮）
    history: List[DialogTurn] = field(default_factory=list)

    # 上下文栈
    context_stack: List[Dict] = field(default_factory=list)

    # 元数据
    turn_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    # 状态标志
    is_completed: bool = False
    needs_clarification: bool = False
    missing_slots: List[str] = field(default_factory=list)

    # 用户画像（可选）
    user_profile: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转为字典"""
        return {
            "session_id": self.session_id,
            "user_phone": self.user_phone,
            "user_name": self.user_name,
            "current_intent": self.current_intent,
            "previous_intent": self.previous_intent,
            "slots": self.slots,
            "history": [t.to_dict() for t in self.history],
            "context_stack": self.context_stack,
            "turn_count": self.turn_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "is_completed": self.is_completed,
            "needs_clarification": self.needs_clarification,
            "missing_slots": self.missing_slots,
            "user_profile": self.user_profile
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DialogState':
        """从字典创建"""
        # 转换时间字段
        data['created_at'] = datetime.fromisoformat(data['created_at'])
        data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        # 转换历史记录
        data['history'] = [DialogTurn.from_dict(t) for t in data.get('history', [])]

        return cls(**data)

    def add_turn(self, role: str, content: str, intent: Optional[str] = None):
        """添加对话轮次"""
        turn = DialogTurn(
            turn_id=self.turn_count + 1,
            role=role,
            content=content,
            intent=intent
        )
        self.history.append(turn)
        self.turn_count += 1
        self.updated_at = datetime.now()

        # 限制历史长度
        if len(self.history) > 20:
            self.history = self.history[-20:]

    def get_recent_history(self, count: int = 5) -> List[DialogTurn]:
        """获取最近的对话历史"""
        return self.history[-count:] if self.history else []