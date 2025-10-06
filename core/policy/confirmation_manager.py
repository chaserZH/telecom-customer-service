"""
确认管理器
"""
import time
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from utils.logger import logger


class ConfirmationManager:
    """确认管理器"""

    def __init__(self):
        """初始化"""
        self.pending_confirmations: Dict[str, Dict] = {}
        self.timeout = 300  # 5分钟超时

    def create_confirmation(self,
                            session_id: str,
                            intent: str,
                            parameters: Dict[str, Any]) -> str:
        """
        创建确认请求

        Args:
            session_id: 会话ID
            intent: 意图
            parameters: 参数

        Returns:
            str: 确认ID
        """
        confirmation_id = f"confirm_{session_id}_{int(time.time())}"

        self.pending_confirmations[confirmation_id] = {
            "session_id": session_id,
            "intent": intent,
            "parameters": parameters,
            "created_at": datetime.now(),
            "status": "pending"
        }

        logger.info(f"[Confirmation] 创建确认: {confirmation_id}")

        # 清理过期确认
        self._cleanup_expired()

        return confirmation_id

    def get_confirmation(self, confirmation_id: str) -> Optional[Dict]:
        """
        获取确认信息

        Args:
            confirmation_id: 确认ID

        Returns:
            Optional[Dict]: 确认信息
        """
        return self.pending_confirmations.get(confirmation_id)

    def handle_confirmation_response(self,
                                     confirmation_id: str,
                                     user_response: str) -> Dict:
        """
        处理确认响应

        Args:
            confirmation_id: 确认ID
            user_response: 用户响应

        Returns:
            Dict: 处理结果
        """
        if confirmation_id not in self.pending_confirmations:
            logger.warning(f"[Confirmation] 确认不存在或已过期: {confirmation_id}")
            return {
                "success": False,
                "error": "确认已过期，请重新操作"
            }

        confirmation = self.pending_confirmations[confirmation_id]

        # 判断用户意图
        if self._is_positive(user_response):
            confirmation["status"] = "confirmed"
            logger.info(f"[Confirmation] 用户确认: {confirmation_id}")

            return {
                "success": True,
                "confirmed": True,
                "intent": confirmation["intent"],
                "parameters": confirmation["parameters"]
            }
        else:
            confirmation["status"] = "cancelled"
            logger.info(f"[Confirmation] 用户取消: {confirmation_id}")

            return {
                "success": True,
                "confirmed": False,
                "message": "已取消操作"
            }

    def _is_positive(self, text: str) -> bool:
        """
        判断是否为肯定回复

        Args:
            text: 用户输入

        Returns:
            bool: 是否肯定
        """
        positive_words = [
            "确认", "是的", "对", "好的", "可以", "确定",
            "yes", "ok", "sure", "嗯", "行"
        ]

        text_lower = text.lower().strip()
        return any(word in text_lower for word in positive_words)

    def _cleanup_expired(self):
        """清理过期确认"""
        now = datetime.now()
        expired_ids = []

        for conf_id, conf in self.pending_confirmations.items():
            if (now - conf["created_at"]).seconds > self.timeout:
                expired_ids.append(conf_id)

        for conf_id in expired_ids:
            del self.pending_confirmations[conf_id]
            logger.debug(f"[Confirmation] 清理过期确认: {conf_id}")