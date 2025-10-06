"""
状态管理器
"""

from datetime import datetime
from core.dst.dialog_state import DialogState
from utils import logger


class StateManager:
    """状态管理器"""

    def initialize_state(self, session_id: str) -> DialogState:
        """初始化新状态"""
        state = DialogState(session_id=session_id)
        logger.info(f"初始化新会话: {session_id}")
        return state

    def validate_state(self, state: DialogState) -> bool:
        """验证状态有效性"""
        if not state.session_id:
            logger.error("状态验证失败: 缺少session_id")
            return False

        # 验证时间戳
        if state.created_at > datetime.now():
            logger.error("状态验证失败: created_at不合法")
            return False

        # 验证轮次数
        if state.turn_count < 0:
            logger.error("状态验证失败: turn_count不合法")
            return False

        return True

    def is_state_expired(self, state: DialogState, timeout_seconds: int = 1800) -> bool:
        """检查状态是否过期"""
        from datetime import timedelta

        if not state.updated_at:
            return False

        age = datetime.now() - state.updated_at
        expired = age > timedelta(seconds=timeout_seconds)

        if expired:
            logger.info(f"会话已过期: {state.session_id}, 最后更新: {state.updated_at}")

        return expired

    def mark_completed(self, state: DialogState):
        """标记状态为完成"""
        state.is_completed = True
        state.updated_at = datetime.now()
        logger.info(f"会话标记为完成: {state.session_id}")

    def reset_clarification(self, state: DialogState):
        """重置澄清标志"""
        state.needs_clarification = False
        state.missing_slots = []