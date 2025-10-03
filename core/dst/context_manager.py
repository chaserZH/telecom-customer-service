"""
上下文管理器
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from utils import logger


class ContextManager:
    """上下文管理器"""

    MAX_CONTEXT_SIZE = 10  # 最大上下文数量
    CONTEXT_TTL = 300  # 上下文存活时间（秒）

    def update_context(self,
                       context_stack: List[Dict],
                       nlu_result) -> List[Dict]:
        """
        更新上下文

        Args:
            context_stack: 当前上下文栈
            nlu_result: NLU解析结果

        Returns:
            更新后的上下文栈
        """
        # 清理过期上下文
        context_stack = self._clean_expired_context(context_stack)

        # 创建新上下文
        new_context = {
            "intent": nlu_result.intent,
            "parameters": nlu_result.parameters,
            "confidence": nlu_result.confidence,
            "timestamp": datetime.now(),
            "turn_id": len(context_stack) + 1
        }

        context_stack.append(new_context)

        # 限制栈大小
        if len(context_stack) > self.MAX_CONTEXT_SIZE:
            removed = len(context_stack) - self.MAX_CONTEXT_SIZE
            context_stack = context_stack[-self.MAX_CONTEXT_SIZE:]
            logger.debug(f"上下文栈超过限制，移除{removed}个旧上下文")

        return context_stack

    def _clean_expired_context(self, context_stack: List[Dict]) -> List[Dict]:
        """清理过期上下文"""
        now = datetime.now()
        threshold = now - timedelta(seconds=self.CONTEXT_TTL)

        cleaned = []
        for ctx in context_stack:
            timestamp = ctx.get("timestamp")
            if isinstance(timestamp, str):
                timestamp = datetime.fromisoformat(timestamp)

            if timestamp and timestamp > threshold:
                cleaned.append(ctx)

        removed_count = len(context_stack) - len(cleaned)
        if removed_count > 0:
            logger.debug(f"清理{removed_count}个过期上下文")

        return cleaned

    def get_recent_context(self, context_stack: List[Dict], count: int = 3) -> List[Dict]:
        """获取最近的上下文"""
        return context_stack[-count:] if context_stack else []

    def find_context_by_intent(self, context_stack: List[Dict], intent: str) -> Optional[Dict]:
        """根据意图查找上下文"""
        for ctx in reversed(context_stack):
            if ctx.get("intent") == intent:
                return ctx
        return None

    def extract_entities_from_context(self, context_stack: List[Dict]) -> Dict[str, Any]:
        """从上下文中提取实体"""
        entities = {}

        # 从最近的上下文中提取
        recent_contexts = self.get_recent_context(context_stack, 5)

        for ctx in recent_contexts:
            params = ctx.get("parameters", {})
            # 用户信息实体优先级最高
            for key in ['phone', 'name', 'user_id']:
                if key in params and params[key]:
                    entities[key] = params[key]

        return entities