"""
策略引擎主类
"""

from typing import Dict, Optional

from core.dst.dialog_state import DialogState
from core.policy.action import Action, ActionType
from core.policy.confirmation_manager import ConfirmationManager
from core.policy.policy_rules import PolicyRules
from utils import logger


class PolicyEngine:
    """对话策略引擎"""

    def __init__(self):
        """初始化策略引擎"""
        self.rules = PolicyRules()
        self.confirmation_manager = ConfirmationManager()
        logger.info("策略引擎初始化完成")

    def decide(self,
               state: DialogState,
               exec_result: Optional[Dict] = None) -> Action:
        """
        决策主函数

        Args:
            state: 对话状态
            exec_result: 执行结果

        Returns:
            Action: 决策的动作
        """
        logger.info(f"[Policy] 开始决策: intent={state.current_intent}, turn={state.turn_count}")

        try:
            # 决策优先级顺序
            # 1. 异常处理
            if exec_result and not exec_result.get("success"):
                return self._handle_error(state, exec_result)

            # 2. 槽位填充
            if state.needs_clarification:
                return self._request_slot(state)

            # 3. 确认流程
            if self._needs_confirmation(state):
                return self._create_confirmation(state)

            # 4. 业务执行成功
            if exec_result and exec_result.get("success"):
                return self._handle_success(state, exec_result)

            # 5. 默认执行动作
            return self._default_action(state)

        except Exception as e:
            logger.error(f"[Policy] 决策异常: {e}", exc_info=True)
            return Action(
                action_type=ActionType.APOLOGIZE,
                intent=state.current_intent or "unknown",
                parameters={"error": "系统繁忙，请稍后再试"}
            )

    def _handle_error(self, state: DialogState, exec_result: Dict) -> Action:
        """
        处理错误

        Args:
            state: 对话状态
            exec_result: 执行结果

        Returns:
            Action: 致歉动作
        """
        error_msg = exec_result.get("error", "处理失败")
        error_type = self._classify_error(exec_result)

        logger.warning(f"[Policy] 处理错误: {error_type} - {error_msg}")

        return Action(
            action_type=ActionType.APOLOGIZE,
            intent=state.current_intent,
            parameters={
                "error": error_msg,
                "error_type": error_type
            },
            template_key=f"apologize_{error_type}"
        )

    def _classify_error(self, exec_result: Dict) -> str:
        """
        分类错误类型

        Args:
            exec_result: 执行结果

        Returns:
            str: 错误类型
        """
        error_msg = exec_result.get("error", "").lower()

        if "not found" in error_msg or "未找到" in error_msg:
            return "not_found"
        elif "invalid" in error_msg or "不正确" in error_msg:
            return "invalid_input"
        elif "database" in error_msg or "数据库" in error_msg:
            return "system_error"
        else:
            return "unknown_error"

    def _request_slot(self, state: DialogState) -> Action:
        """
        请求槽位填充

        Args:
            state: 对话状态

        Returns:
            Action: 请求动作
        """
        missing_slot = state.missing_slots[0] if state.missing_slots else "unknown"

        logger.info(f"[Policy] 请求槽位: {missing_slot}")

        return Action(
            action_type=ActionType.REQUEST,
            intent=state.current_intent,
            parameters={
                "slot": missing_slot,
                "context": state.slots
            },
            template_key=f"request_{missing_slot}"
        )

    def _needs_confirmation(self, state: DialogState) -> bool:
        """
        判断是否需要确认

        Args:
            state: 对话状态

        Returns:
            bool: 是否需要确认
        """
        # 应用确认规则
        return self.rules.apply_confirmation_rules(state)

    def _create_confirmation(self, state: DialogState) -> Action:
        """
        创建确认动作

        Args:
            state: 对话状态

        Returns:
            Action: 确认动作
        """
        logger.info(f"[Policy] 创建确认: intent={state.current_intent}")

        # 创建确认记录
        confirmation_id = self.confirmation_manager.create_confirmation(
            state.session_id,
            state.current_intent,
            state.slots
        )

        return Action(
            action_type=ActionType.CONFIRM,
            intent=state.current_intent,
            parameters={
                **state.slots,
                "confirmation_id": confirmation_id
            },
            requires_confirmation=True,
            template_key=f"confirm_{state.current_intent}"
        )

    def _handle_success(self, state: DialogState, exec_result: Dict) -> Action:
        """
        处理成功结果

        Args:
            state: 对话状态
            exec_result: 执行结果

        Returns:
            Action: 告知动作
        """
        logger.info(f"[Policy] 处理成功结果: intent={state.current_intent}")

        # 创建基本动作
        action = Action(
            action_type=ActionType.INFORM,
            intent=state.current_intent,
            parameters=exec_result
        )

        # 应用推荐规则
        if self.rules.should_recommend(state, exec_result):
            action.parameters["should_recommend"] = True
            action.use_llm = True  # 推荐使用LLM生成
            logger.info("[Policy] 触发推荐")

        # 应用引导规则
        guidance = self.rules.apply_guidance_rules(state, exec_result)
        if guidance:
            action.parameters["guidance"] = guidance

        return action

    def _default_action(self, state: DialogState) -> Action:
        """
        默认动作

        Args:
            state: 对话状态

        Returns:
            Action: 执行动作
        """
        logger.info(f"[Policy] 默认动作: intent={state.current_intent}")

        return Action(
            action_type=ActionType.EXECUTE,
            intent=state.current_intent,
            parameters=state.slots
        )