"""
第三阶段完整对话系统 - 整合Policy + NLG
修复版：正确的确认流程
"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from core.nlu import NLUEngine
from core.dst import DialogStateTracker, DialogState
from core.policy import PolicyEngine, ActionType, Action
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
            # ========== 阶段0: 检查是否是确认响应 ⭐ ==========
            # 先加载状态，检查是否有待确认的操作
            current_state = self.dst.get_state(session_id)

            if current_state.pending_confirmation:
                logger.info("【阶段0】检测到待确认状态，处理确认响应...")
                confirmation_result = self._handle_confirmation_response(
                    user_input,
                    session_id,
                    current_state
                )
                if confirmation_result:
                    return confirmation_result
                # 如果不是确认/取消，继续正常流程（用户可能换了话题）

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

            # ========== 阶段3a: Policy预决策 ⭐ ==========
            logger.info("【阶段3a】Policy预决策...")

            # 先判断是否需要确认（不传执行结果）
            action = self.policy.decide(dialog_state, exec_result=None)
            logger.info(f"✓ Policy预决策: action={action.action_type.value}, "
                        f"needs_confirmation={action.requires_confirmation}")

            # ========== 阶段3b: 条件执行业务 ⭐ ==========
            exec_result = None

            if action.action_type == ActionType.CONFIRM:
                # 🔥 需要确认：不执行业务，保存待确认状态
                logger.info("【阶段3b】需要确认，保存待确认状态，跳过业务执行")
                dialog_state.set_pending_confirmation(
                    dialog_state.current_intent,
                    dialog_state.slots
                )
                self.dst.state_store.save(session_id, dialog_state)

            elif not dialog_state.needs_clarification and dialog_state.current_intent:
                # 🔥 不需要确认：执行业务
                logger.info("【阶段3b】执行业务...")
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

                # 执行后重新决策（因为有了执行结果）
                logger.info("【阶段3b-2】Policy重新决策（含执行结果）...")
                action = self.policy.decide(dialog_state, exec_result)
                logger.info(f"✓ Policy最终决策: action={action.action_type.value}")

            # ========== 阶段3c: NLG生成 ⭐ ==========
            logger.info("【阶段3c】NLG生成回复...")
            response_text = self.nlg.generate(action, dialog_state)

            # 🔥 可选：如果新意图执行成功，但还有未完成的待确认操作，友好提醒
            if (action.action_type == ActionType.INFORM and
                    exec_result and exec_result.get("success") and
                    dialog_state.pending_confirmation):
                pending_desc = self._get_pending_description(
                    dialog_state.confirmation_intent
                )
                response_text += f"\n\n💡 提示：您还有一个待确认的{pending_desc}，" \
                                 f"如需继续请回复\"确认\"，取消请回复\"取消\""

            logger.info(f"✓ NLG完成: 长度={len(response_text)}")

            # ========== 阶段4: 更新状态 ==========
            logger.info(f"✓ 更新状态")
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
                    "needs_clarification": dialog_state.needs_clarification,
                    "pending_confirmation": dialog_state.pending_confirmation
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

    def _handle_confirmation_response(self,
                                      user_input: str,
                                      session_id: str,
                                      dialog_state: DialogState) -> Optional[Dict]:
        """
        处理确认响应（增强版）
        """
        # 🔥 先检查是否超时
        if dialog_state.is_confirmation_expired():
            logger.warning("【确认处理】待确认操作已超时")
            dialog_state.clear_pending_confirmation()

            return {
                "session_id": session_id,
                "response": "抱歉，确认已超时。如需办理，请重新发起。还有什么可以帮您的吗？",
                "action": "INFORM",
                "intent": "timeout",
                "requires_confirmation": False,
                "data": None,
                "state": {
                    "turn_count": dialog_state.turn_count,
                    "slots": {},
                    "needs_clarification": False,
                    "pending_confirmation": False
                },
                "metadata": {
                    "execution_time_ms": 0,
                    "timestamp": datetime.now().isoformat()
                }
            }

        # 检查是否是确认词
        if self._is_confirmation_word(user_input):
            logger.info("【确认处理】用户确认操作")

            # 🔥 记录确认的意图和参数（用于日志）
            logger.info(f"执行待确认操作: {dialog_state.confirmation_intent}, "
                        f"参数: {dialog_state.confirmation_slots}")

            # 执行待确认的业务
            exec_result = self.db_executor.execute_function(
                dialog_state.confirmation_intent,
                dialog_state.confirmation_slots
            )

            # 清除待确认状态
            dialog_state.clear_pending_confirmation()

            # 生成回复
            if exec_result and exec_result.get("success"):
                action = Action(
                    action_type=ActionType.INFORM,
                    intent=dialog_state.confirmation_intent,
                    parameters=exec_result
                )
                response_text = self.nlg.generate(action, dialog_state)
            else:
                action = Action(
                    action_type=ActionType.APOLOGIZE,
                    intent=dialog_state.confirmation_intent,
                    parameters=exec_result or {"error": "执行失败"}
                )
                response_text = self.nlg.generate(action, dialog_state)

            # 更新状态
            dialog_state.add_turn('assistant', response_text)
            self.dst.state_store.save(session_id, dialog_state)

            return {
                "session_id": session_id,
                "response": response_text,
                "action": action.action_type.value,
                "intent": dialog_state.confirmation_intent,
                "requires_confirmation": False,
                "data": exec_result,
                "state": {
                    "turn_count": dialog_state.turn_count,
                    "slots": dialog_state.confirmation_slots,
                    "needs_clarification": False,
                    "pending_confirmation": False
                },
                "metadata": {
                    "execution_time_ms": 0,
                    "timestamp": datetime.now().isoformat()
                }
            }

        # 检查是否是取消词
        elif self._is_cancellation_word(user_input):
            logger.info("【确认处理】用户取消操作")

            # 清除待确认状态
            dialog_state.clear_pending_confirmation()

            # 更新状态
            response_text = "已取消操作。还有什么可以帮您的吗？"
            dialog_state.add_turn('assistant', response_text)
            self.dst.state_store.save(session_id, dialog_state)

            return {
                "session_id": session_id,
                "response": response_text,
                "action": "INFORM",
                "intent": "cancel",
                "requires_confirmation": False,
                "data": None,
                "state": {
                    "turn_count": dialog_state.turn_count,
                    "slots": {},
                    "needs_clarification": False,
                    "pending_confirmation": False
                },
                "metadata": {
                    "execution_time_ms": 0,
                    "timestamp": datetime.now().isoformat()
                }
            }

        # 🔥 不是确认/取消，但有待确认状态
        # 返回 None，让系统继续正常流程（处理新意图）
        # DST 中已经根据意图相关性决定是否清除待确认状态
        logger.info("【确认处理】用户输入不是确认/取消，继续正常流程")
        return None

    def _is_confirmation_word(self, text: str) -> bool:
        """判断是否为确认词"""
        confirmation_words = [
            "确认", "确定", "是的", "是", "对", "好的", "可以",
            "ok", "yes", "嗯", "行", "同意", "没问题", "办理"
        ]

        text_lower = text.lower().strip()
        return any(word in text_lower for word in confirmation_words)

    def _is_cancellation_word(self, text: str) -> bool:
        """判断是否为取消词"""
        cancellation_words = [
            "取消", "不", "不要", "算了", "不办", "不确认",
            "no", "cancel", "不行", "不用"
        ]

        text_lower = text.lower().strip()
        return any(word in text_lower for word in cancellation_words)

    def get_session_state(self, session_id: str) -> Dict:
        """获取会话状态（用于调试）"""
        state = self.dst.get_state(session_id)
        return state.to_dict()

    def reset_session(self, session_id: str):
        """重置会话"""
        self.dst.reset_state(session_id)
        logger.info(f"重置会话: {session_id}")

    def get_cache_stats(self) -> dict:
        """获取缓存统计"""
        return self.cache.stats()

    def _get_pending_description(self, intent: str) -> str:
        """获取待确认操作的描述"""
        descriptions = {
            "change_package": "套餐办理",
            "cancel_service": "服务取消",
            "upgrade_package": "套餐升级"
        }
        return descriptions.get(intent, "操作")
