# core/nlu/result_validator.py
"""
NLU结果后验证器 - 规则二次验证
"""
import re
from typing import Dict, Any, List, Optional
from utils import logger


class ResultValidator:
    """NLU结果验证器"""

    def __init__(self):
        """初始化验证规则"""
        self.package_names = ["经济套餐", "畅游套餐", "无限套餐", "校园套餐"]

        # 意图-参数依赖关系
        self.intent_param_rules = {
            "change_package": {
                "required": ["new_package_name"],  # 必须有套餐名
                "optional": ["phone"]
            },
            "query_current_package": {
                "required": ["phone"],  # 必须有手机号
                "optional": []
            },
            "query_package_detail": {
                "required": ["package_name"],  # 必须有套餐名
                "optional": []
            },
            "query_packages": {
                "required": [],  # 可以无参数
                "optional": ["price_max", "price_min", "data_min"]
            }
        }

        logger.info("✓ 验证器初始化完成")

    def validate(self,
                 intent: str,
                 parameters: Dict[str, Any],
                 user_input: str,
                 context: Dict) -> Dict[str, Any]:
        """
        验证NLU结果的合理性

        Args:
            intent: 识别的意图
            parameters: 提取的参数
            user_input: 原始用户输入
            context: 会话上下文

        Returns:
            Dict: 验证结果
                {
                    "valid": bool,              # 是否有效
                    "corrected_intent": str,    # 修正后的意图
                    "corrected_params": dict,   # 修正后的参数
                    "warnings": list,           # 警告信息
                    "confidence": float         # 修正后的置信度
                }
        """
        logger.info(f"[后验证] 开始验证: intent={intent}, params={parameters}")

        result = {
            "valid": True,
            "corrected_intent": intent,
            "corrected_params": parameters.copy(),
            "warnings": [],
            "confidence": 1.0
        }

        # 验证1: 意图-输入一致性
        intent_check = self._check_intent_consistency(intent, user_input, context)
        if not intent_check["valid"]:
            result["valid"] = False
            result["corrected_intent"] = intent_check["suggested_intent"]
            result["warnings"].append(intent_check["reason"])
            result["confidence"] *= 0.7

        # 验证2: 参数完整性
        param_check = self._check_parameters(intent, parameters, user_input)
        if not param_check["valid"]:
            result["warnings"].append(param_check["reason"])
            result["corrected_params"] = param_check["corrected_params"]
            result["confidence"] *= 0.8

        # 验证3: 参数合理性
        reasonability_check = self._check_reasonability(intent, parameters)
        if not reasonability_check["valid"]:
            result["warnings"].append(reasonability_check["reason"])
            result["confidence"] *= 0.9

        # 验证4: 上下文一致性
        context_check = self._check_context_consistency(intent, parameters, context)
        if not context_check["valid"]:
            result["warnings"].extend(context_check["warnings"])
            result["corrected_params"].update(context_check["corrections"])

        logger.info(
            f"[后验证] 完成: valid={result['valid']}, "
            f"warnings={len(result['warnings'])}, "
            f"confidence={result['confidence']:.2f}"
        )

        return result

    def _check_intent_consistency(self, intent: str, user_input: str, context: Dict) -> Dict:
        """验证意图与输入的一致性"""

        # 规则1: "怎么"开头 → 应该是 business_consultation
        if user_input.startswith(("怎么", "如何", "怎样")):
            if intent != "business_consultation":
                return {
                    "valid": False,
                    "suggested_intent": "business_consultation",
                    "reason": "疑问词开头应该是咨询意图"
                }

        # 规则2: "我要办理套餐"（无具体名） → 应该是 query_packages
        if intent == "change_package":
            has_package_name = any(pkg in user_input for pkg in self.package_names)
            has_context_package = context.get("slot_values", {}).get("package_name") or \
                                  context.get("slot_values", {}).get("new_package_name")

            if not has_package_name and not has_context_package:
                return {
                    "valid": False,
                    "suggested_intent": "query_packages",
                    "reason": "无具体套餐名时，应先展示列表"
                }

        # 规则3: "我的套餐" → 应该是 query_current_package
        if "我的" in user_input and "套餐" in user_input:
            if intent not in ["query_current_package", "query_usage"]:
                return {
                    "valid": False,
                    "suggested_intent": "query_current_package",
                    "reason": "查询自己的套餐"
                }

        return {"valid": True}

    def _check_parameters(self, intent: str, parameters: Dict, user_input: str) -> Dict:
        """验证参数完整性"""

        if intent not in self.intent_param_rules:
            return {"valid": True, "corrected_params": parameters}

        rules = self.intent_param_rules[intent]
        required = rules["required"]

        # 检查必填参数
        missing = []
        for param in required:
            if param not in parameters or not parameters[param]:
                missing.append(param)

        if missing:
            return {
                "valid": False,
                "reason": f"缺少必填参数: {missing}",
                "corrected_params": parameters
            }

        # 特殊处理：套餐名验证
        if "new_package_name" in parameters or "package_name" in parameters:
            key = "new_package_name" if "new_package_name" in parameters else "package_name"
            pkg_name = parameters[key]

            if pkg_name not in self.package_names:
                # 尝试模糊匹配
                corrected = self._fuzzy_match_package(pkg_name)
                if corrected:
                    return {
                        "valid": True,
                        "reason": f"套餐名模糊匹配: {pkg_name} → {corrected}",
                        "corrected_params": {**parameters, key: corrected}
                    }
                else:
                    return {
                        "valid": False,
                        "reason": f"无效的套餐名: {pkg_name}",
                        "corrected_params": parameters
                    }

        return {"valid": True, "corrected_params": parameters}

    def _check_reasonability(self, intent: str, parameters: Dict) -> Dict:
        """验证参数合理性"""

        # 验证价格范围
        if "price_max" in parameters:
            if parameters["price_max"] < 0 or parameters["price_max"] > 1000:
                return {
                    "valid": False,
                    "reason": f"价格不合理: {parameters['price_max']}"
                }

        # 验证流量范围
        if "data_min" in parameters:
            if parameters["data_min"] < 0 or parameters["data_min"] > 10000:
                return {
                    "valid": False,
                    "reason": f"流量不合理: {parameters['data_min']}"
                }

        # 验证手机号格式
        if "phone" in parameters:
            phone = str(parameters["phone"])
            if not re.match(r'^1[3-9]\d{9}$', phone):
                return {
                    "valid": False,
                    "reason": f"手机号格式错误: {phone}"
                }

        return {"valid": True}

    def _check_context_consistency(self, intent: str, parameters: Dict, context: Dict) -> Dict:
        """验证上下文一致性"""
        warnings = []
        corrections = {}

        # 如果是办理场景，检查是否可以从上下文继承套餐名
        if intent == "change_package" and "new_package_name" not in parameters:
            slot_values = context.get("slot_values", {})
            if "package_name" in slot_values:
                corrections["new_package_name"] = slot_values["package_name"]
                warnings.append(f"从上下文继承套餐名: {slot_values['package_name']}")

        # 检查是否可以从上下文继承手机号
        if "phone" not in parameters:
            slot_values = context.get("slot_values", {})
            if "phone" in slot_values:
                corrections["phone"] = slot_values["phone"]
                warnings.append(f"从上下文继承手机号")

        return {
            "valid": len(warnings) == 0 or len(corrections) > 0,
            "warnings": warnings,
            "corrections": corrections
        }

    def _fuzzy_match_package(self, input_name: str) -> Optional[str]:
        """模糊匹配套餐名"""
        # 简单的相似度匹配
        for pkg in self.package_names:
            # 移除"套餐"后比较
            input_clean = input_name.replace("套餐", "")
            pkg_clean = pkg.replace("套餐", "")

            if input_clean in pkg_clean or pkg_clean in input_clean:
                return pkg

        return None