"""
第三阶段完整对话系统 - 整合Policy + NLG
"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from core.nlu import NLUEngine
from core.dst import DialogStateTracker
from core.policy import PolicyEngine
from core.nlg import NLGGenerator
from core.recommendation import RecommendationEngine
from executor.db_executor import DatabaseExecutor
from utils.logger import logger
from utils.cache import ResponseCache


class TelecomChatbotPolicy:
    """电信客服对话系统 - 第三阶段（Policy + NLG）"""

    def __init__(self):
        """初始化对话系统"""
        # 第一阶段：NLU
        self.nlu = NLUEngine()

        # 第二阶段：DST
        self.dst = DialogStateTracker()

        # 第三阶段：Policy + NLG ⭐
        self.policy = PolicyEngine()
        self.nlg = NLGGenerator()

        # 高级特性
        self.recommendation = RecommendationEngine()

        # 执行器
        self.db_executor = DatabaseExecutor()

        # 性能优化：缓存
        self.cache = ResponseCache(ttl=300, max_size=1000)

        logger.info("=" * 60)
        logger.info("第三阶段对话系统初始化完成（Policy + NLG）")
        logger.info("=" * 60)

    def chat(self,
             user_input: str,
             session_id: Optional[str] = None,
             user_phone: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户输入

        Args:
            user_input: 用户输入文本
            session_id: 会话ID（可选，自动生成）
            user_phone: 用户手机号（可选）

        Returns:
            Dict: 响应字典
        """
        start_time = datetime.now()

        # 生成会话ID
        if not session_id:
            session_id = str(uuid.uuid4())

        logger.info(f"\n{'=' * 60}")
        logger.info(f"[{session_id}] 收到用户输入: {user_input}")
        logger.info(f"{'=' * 60}")

        try:
            # ========== 阶段1: NLU理解 ==========
            logger.info("【阶段1】NLU理解...")
            nlu_result = self.nlu.understand(user_input, session_id, user_phone)
            nlu_result.raw_input = user_input
            logger.info(f"✓ NLU完成: intent={nlu_result.intent}")

            # ========== 阶段2: DST状态跟踪 ==========
            logger.info("【阶段2】DST状态跟踪...")
            dialog_state = self.dst.track(session_id, nlu_result)
            logger.info(f"✓ DST完成: turn={dialog_state.turn_count}, "
                        f"needs_clarification={dialog_state.needs_clarification}")

            # ========== 阶段3a: 业务执行 ==========
            exec_result = None
            if not dialog_state.needs_clarification and dialog_state.current_intent:
                logger.info("【阶段3a】执行业务...")
                exec_result = self.db_executor.execute_function(
                    dialog_state.current_intent,
                    dialog_state.slots
                )

                # 如果是查询套餐，生成推荐
                if (dialog_state.current_intent == "query_packages" and
                        exec_result and exec_result.get("success")):
                    recommendation = self.recommendation.recommend(
                        dialog_state,
                        exec_result
                    )
                    if recommendation:
                        exec_result["recommendation"] = recommendation
                        logger.info(f"✓ 生成推荐: {recommendation['package']['name']}")

            # ========== 阶段3b: Policy决策 ⭐ ==========
            logger.info("【阶段3b】Policy决策...")
            action = self.policy.decide(dialog_state, exec_result)
            logger.info(f"✓ Policy决策: action={action.action_type.value}")

            # ========== 阶段3c: NLG生成 ⭐ ==========
            logger.info("【阶段3c】NLG生成回复...")

            # 尝试从缓存获取
            cache_key = ResponseCache.generate_key(
                action.action_type.value,
                action.intent,
                action.parameters
            )

            response_text = None
            if cache_key:
                response_text = self.cache.get(cache_key)

            # 未命中缓存，生成新响应
            if not response_text:
                response_text = self.nlg.generate(action, dialog_state)
                # 缓存确定性响应
                if cache_key:
                    self.cache.set(cache_key, response_text)

            logger.info(f"✓ NLG完成: 长度={len(response_text)}")

            # ========== 阶段4: 更新状态 ==========
            dialog_state.add_turn('assistant', response_text)
            self.dst.state_store.save(session_id, dialog_state)

            # ========== 构建响应 ==========
            execution_time = (datetime.now() - start_time).total_seconds() * 1000

            response = {
                "session_id": session_id,
                "response": response_text,
                "action": action.action_type.value,
                "intent": dialog_state.current_intent,
                "requires_confirmation": action.requires_confirmation,
                "data": exec_result,
                "state": {
                    "turn_count": dialog_state.turn_count,
                    "slots": dialog_state.slots,
                    "needs_clarification": dialog_state.needs_clarification
                },
                "metadata": {
                    "execution_time_ms": round(execution_time, 2),
                    "timestamp": datetime.now().isoformat()
                }
            }

            logger.info(f"✓ 对话完成，耗时: {execution_time:.0f}ms")
            logger.info(f"{'=' * 60}\n")

            return response

        except Exception as e:
            logger.error(f"[{session_id}] 处理异常: {e}", exc_info=True)
            return {
                "session_id": session_id,
                "response": f"抱歉，系统遇到了问题，请稍后再试",
                "action": "APOLOGIZE",
                "intent": "error",
                "requires_input": False,
                "timestamp": datetime.now().isoformat()
            }

    def get_session_state(self, session_id: str) -> Dict:
        """
        获取会话状态（用于调试）

        Args:
            session_id: 会话ID

        Returns:
            Dict: 会话状态
        """
        state = self.dst.get_state(session_id)
        return state.to_dict()

    def reset_session(self, session_id: str):
        """
        重置会话

        Args:
            session_id: 会话ID
        """
        self.dst.reset_state(session_id)
        logger.info(f"重置会话: {session_id}")

    def get_cache_stats(self) -> dict:
        """
        获取缓存统计

        Returns:
            dict: 缓存统计信息
        """
        return self.cache.stats()


