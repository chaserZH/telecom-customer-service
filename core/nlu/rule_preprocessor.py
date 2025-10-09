"""
规则前置处理器 - 处理80%高频场景
"""
import re
from typing import Optional, Dict, Any, List

from .rule_definitions import PRE_NLU_RULES
from utils import logger


class RulePreprocessor:
    """规则前置处理器"""

    def __init__(self):
        """初始化规则库"""
        # 套餐名称
        self.package_names = ["经济套餐", "畅游套餐", "无限套餐", "校园套餐"]
        # 高频规则库（优先级从高到低）
        self.rules = PRE_NLU_RULES
        # 按优先级排序
        self.rules.sort(key=lambda x: x.get("priority", 0), reverse=True)

        logger.info(f"✓ 规则库初始化完成: {len(self.rules)}条规则")

    def preprocess(self, user_input: str, context: Dict) -> Optional[Dict[str, Any]]:
        """
        规则预处理 - 尝试用规则匹配

        Args:
            user_input: 用户输入
            context: 会话上下文

        Returns:
            Dict: 如果规则命中，返回 {intent, parameters, source, confidence}
            None: 如果规则未命中，返回None（交给LLM）
        """
        logger.info(f"[规则匹配] 开始匹配: {user_input}")

        for rule in self.rules:
            # 检查是否需要上下文
            if rule.get("context_required") and not context.get("current_intent"):
                continue
            # 正则匹配
            match = re.search(rule["pattern"], user_input, re.IGNORECASE)

            if match:
                # 命中规则
                intent = rule["intent"]

                # 提取参数
                parameters = self._extract_parameters(
                    user_input,
                    match,
                    rule["extract"],
                    context,
                    rule
                )

                # 特殊处理：上下文继承
                if rule.get("context_required"):
                    parameters = self._inherit_from_context(parameters, context)

                logger.info(
                    f"[规则命中] 规则='{rule['name']}', "
                    f"意图={intent}, 参数={parameters}"
                )

                return {
                    "intent": intent,
                    "parameters": parameters,
                    "source": "rule",
                    "confidence": 0.95,
                    "rule_name": rule["name"]
                }

        logger.info("[规则匹配] 未命中，交给LLM")
        return None

    def _extract_parameters(self,
                            text: str,
                            match,
                            extract_list: List[str],
                            context: Dict,
                            rule: Dict) -> Dict:
        """提取参数"""
        params = {}

        # 1. 提取套餐名（new_package_name 或 package_name）
        if "new_package_name" in extract_list or "package_name" in extract_list:
            for pkg in self.package_names:
                if pkg in text:
                    key = "new_package_name" if "new_package_name" in extract_list else "package_name"
                    params[key] = pkg
                    break

        # 2. 提取手机号
        if "phone" in extract_list:
            phone_match = re.search(r'1[3-9]\d{9}', text)
            if phone_match:
                params["phone"] = phone_match.group()
            elif context.get("user_phone"):
                params["phone"] = context["user_phone"]
            # 如果没有，留空（后续追问）

        # 3. 提取价格范围
        if "price_max" in extract_list:
            price_match = re.search(r'(\d+)\s*[元块]', text)
            if price_match:
                params["price_max"] = int(price_match.group(1))

        # 4. 提取流量需求
        if "data_min" in extract_list:
            data_match = re.search(r'(\d+)\s*[G|GB]', text, re.IGNORECASE)
            if data_match:
                params["data_min"] = int(data_match.group(1))

        # 5. 提取咨询问题
        if "question" in extract_list:
            params["question"] = text
            params["business_type"] = "办理流程"  # 默认

        return params

    def _inherit_from_context(self, parameters: Dict, context: Dict) -> Dict:
        """从上下文继承参数"""
        # 继承套餐名（如果当前没有）
        if "new_package_name" not in parameters:
            # 从上下文的slot_values中查找
            slot_values = context.get("slot_values", {})
            if "package_name" in slot_values:
                parameters["new_package_name"] = slot_values["package_name"]
            elif "new_package_name" in slot_values:
                parameters["new_package_name"] = slot_values["new_package_name"]

        # 继承手机号
        if "phone" not in parameters:
            slot_values = context.get("slot_values", {})
            if "phone" in slot_values:
                parameters["phone"] = slot_values["phone"]

        return parameters