"""
策略规则库
"""
from typing import Dict, Any, Optional
from core.dst.dialog_state import DialogState
from utils import logger


class PolicyRules:
    """策略规则集"""

    # 需要确认的意图
    RISKY_INTENTS = {
        "change_package",
        "cancel_service"
    }

    # 价格阈值（超过此价格需要确认）
    PRICE_THRESHOLD = 200

    def apply_confirmation_rules(self, state: DialogState) -> bool:
        """
        应用确认规则

        Args:
            state: 对话状态

        Returns:
            bool: 是否需要确认
        """
        # 规则1: 高风险操作需要确认
        if state.current_intent in self.RISKY_INTENTS:
            if not state.user_profile.get("confirmed"):
                logger.info(f"[Rule] 高风险操作需要确认: {state.current_intent}")
                return True

        # 规则2: 高价套餐需要确认
        price = state.slots.get("price") or state.slots.get("new_package_price")
        if price and float(price) > self.PRICE_THRESHOLD:
            logger.info(f"[Rule] 高价套餐需要确认: {price}元")
            return True

        return False

    def should_recommend(self, state: DialogState, exec_result: Dict) -> bool:
        """
        判断是否需要推荐

        Args:
            state: 对话状态
            exec_result: 执行结果

        Returns:
            bool: 是否需要推荐
        """
        # 规则1: 查询结果过多时推荐
        count = exec_result.get("count", 0)
        if count > 3:
            logger.info(f"[Rule] 结果过多，触发推荐: count={count}")
            return True

        # 规则2: 价格敏感用户推荐经济套餐
        price_max = state.slots.get("price_max")
        if price_max and float(price_max) < 100:
            logger.info(f"[Rule] 价格敏感用户，触发推荐: price_max={price_max}")
            return True

        return False

    def apply_guidance_rules(self,
                             state: DialogState,
                             exec_result: Dict) -> Optional[str]:
        """
        应用引导规则

        Args:
            state: 对话状态
            exec_result: 执行结果

        Returns:
            Optional[str]: 引导话术
        """
        # 规则1: 无结果时引导调整条件
        if exec_result.get("count", 0) == 0:
            return "您可以调整一下筛选条件，比如放宽价格或流量要求"

        # 规则2: 学生身份引导校园套餐
        if state.user_profile.get("is_student"):
            packages = exec_result.get("data", [])
            has_campus = any(p.get("name") == "校园套餐" for p in packages)
            if not has_campus:
                return "作为学生用户，您还可以了解一下我们的校园套餐"

        return None
