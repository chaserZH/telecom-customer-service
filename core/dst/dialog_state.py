"""
对话状态数据结构
"""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from utils import logger


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

    # 🔥 新增：确认状态管理
    pending_confirmation: bool = False  # 是否有待确认的操作
    confirmation_intent: Optional[str] = None  # 待确认的意图
    confirmation_slots: Dict[str, Any] = field(default_factory=dict)  # 待确认的参数
    confirmation_timestamp: Optional[datetime] = None  # 🆕 确认请求时间

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
            "user_profile": self.user_profile,
            # 🔥 必须包含这些字段
            "pending_confirmation": self.pending_confirmation,
            "confirmation_intent": self.confirmation_intent,
            "confirmation_slots": self.confirmation_slots,
            "confirmation_timestamp": self.confirmation_timestamp.isoformat() if self.confirmation_timestamp else None,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> 'DialogState':
        """从字典创建"""
        # 转换时间字段
        if isinstance(data['created_at'], str):
            data['created_at'] = datetime.fromisoformat(data['created_at'])
        if isinstance(data['updated_at'], str):
            data['updated_at'] = datetime.fromisoformat(data['updated_at'])

        # 🔥 新增：转换确认时间戳
        if 'confirmation_timestamp' in data and data['confirmation_timestamp']:
            if isinstance(data['confirmation_timestamp'], str):
                data['confirmation_timestamp'] = datetime.fromisoformat(data['confirmation_timestamp'])

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

    def set_pending_confirmation(self, intent: str, slots: Dict[str, Any]):
        """设置待确认状态"""
        self.pending_confirmation = True
        self.confirmation_intent = intent
        self.confirmation_slots = dict(slots)
        self.confirmation_timestamp = datetime.now()  # 🆕 记录时间
        self.updated_at = datetime.now()

    def clear_pending_confirmation(self):
        """清除待确认状态"""
        self.pending_confirmation = False
        self.confirmation_intent = None
        self.confirmation_slots = {}
        self.confirmation_timestamp = None  # 🆕 清除时间
        self.updated_at = datetime.now()

    def is_confirmation_expired(self, timeout_minutes: int = 5) -> bool:
        """检查确认是否超时"""
        if not self.pending_confirmation or not self.confirmation_timestamp:
            return False

        # 🔥 防御性编程：确保是 datetime 对象
        if isinstance(self.confirmation_timestamp, str):
            logger.warning("confirmation_timestamp 是字符串，尝试转换")
            try:
                self.confirmation_timestamp = datetime.fromisoformat(self.confirmation_timestamp)
            except Exception as e:
                logger.error(f"转换失败: {e}")
                return True  # 转换失败视为超时

        elapsed = datetime.now() - self.confirmation_timestamp
        return elapsed > timedelta(minutes=timeout_minutes)
