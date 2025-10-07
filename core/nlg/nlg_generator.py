"""
NLG生成器主类
"""
import json
import random
from typing import Optional, Dict, Any

from core.policy.action import Action, ActionType
from core.dst.dialog_state import DialogState
from core.nlg.templates import RESPONSE_TEMPLATES
from core.nlg.response_formatter import ResponseFormatter
from config import settings
from utils.logger import logger


class NLGGenerator:
    """自然语言生成器"""

    # NLG System Prompt
    NLG_SYSTEM_PROMPT = """你是一个专业的电信客服，负责生成自然、友好的回复。

【生成原则】
1. 语气亲切专业，不过分热情
2. 信息准确完整，突出关键点
3. 简洁明了，避免冗余
4. 根据用户特征调整风格

【输出要求】
- 直接输出回复文本，无需任何标记
- 长度控制在150字以内
- 可以使用emoji增强可读性（适度）
- 不要重复用户已知的信息
"""

    def __init__(self):
        """初始化NLG生成器"""
        self.templates = RESPONSE_TEMPLATES
        self.formatter = ResponseFormatter()

        # 初始化LLM客户端
        if settings.LLM_PROVIDER == "deepseek":
            from openai import OpenAI
            self.llm_client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            self.llm_model = settings.DEEPSEEK_MODEL
        else:
            from openai import OpenAI
            self.llm_client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.llm_model = settings.OPENAI_MODEL

        logger.info("NLG生成器初始化完成")

    def generate(self, action: Action, state: DialogState) -> str:
        """
        生成回复

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 生成的回复文本
        """
        logger.info(f"[NLG] 生成回复: action={action.action_type.value}, intent={action.intent}")

        try:
            # 选择生成策略
            strategy = self._choose_strategy(action, state)

            # 根据策略生成
            if strategy == "template":
                response = self._generate_from_template(action, state)
            elif strategy == "llm":
                response = self._generate_from_llm(action, state)
            else:  # hybrid
                response = self._generate_hybrid(action, state)

            # 后处理
            guidance = action.parameters.get("guidance")
            response = self.formatter.post_process(response, state, guidance)

            logger.info(f"[NLG] 生成成功，长度: {len(response)}")
            return response

        except Exception as e:
            logger.error(f"[NLG] 生成失败: {e}", exc_info=True)
            return self._fallback_response(action)

    def _choose_strategy(self, action: Action, state: DialogState) -> str:
        """
        选择生成策略

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 策略名称 (template/llm/hybrid)
        """
        # 强制使用LLM
        if action.use_llm:
            return "llm"

        # REQUEST和CONFIRM总是用模板
        if action.action_type in [ActionType.REQUEST, ActionType.CONFIRM]:
            return "template"

        # 推荐场景用LLM
        if action.parameters.get("should_recommend"):
            return "llm"

        # 多结果对比用LLM
        if action.parameters.get("count", 0) > 3:
            return "llm"

        # 其他用模板
        return "template"

    def _generate_from_template(self, action: Action, state: DialogState) -> str:
        """
        从模板生成

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 生成的文本
        """
        # 选择模板
        template = self._select_template(action, state)
        logger.info(f"选择模版为={template}")

        # 准备参数
        params = self._prepare_template_params(action, state)

        try:
            # 格式化模板
            response = template.format(**params)
            logger.info(f"[NLG] 模板生成成功")
            return response
        except KeyError as e:
            logger.error(f"[NLG] 模板参数缺失: {e}")
            return self._fallback_response(action)

    def _select_template(self, action: Action, state: DialogState) -> str:
        """
        选择模板

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 模板字符串
        """
        action_type = action.action_type.value if isinstance(action.action_type, ActionType) else action.action_type

        # 获取动作类型的模板
        action_templates = self.templates.get(action_type, {})

        # 如果指定了模板键
        if action.template_key and action.template_key in action_templates:
            template = action_templates[action.template_key]
        # 否则按意图查找
        elif action.intent in action_templates:
            template = action_templates[action.intent]
        else:
            template = action_templates.get("default", "处理完成")

        # 如果是字典，按数据特征选择
        if isinstance(template, dict):
            count = action.parameters.get("count", 0)
            if count == 0:
                template = template.get("empty", template.get("default", ""))
            elif count == 1:
                data = action.parameters.get("data", [{}])[0]
                template = template.get("single", template.get("default", ""))
                # 将单个数据扁平化到参数中
                action.parameters.update(data)
            else:
                template = template.get("multiple", template.get("default", ""))

        # 如果是列表，随机选择
        if isinstance(template, list):
            template = random.choice(template)

        return template

    def _prepare_template_params(self, action: Action, state: DialogState) -> Dict[str, Any]:
        """
        准备模板参数

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            Dict: 参数字典
        """
        params = dict(action.parameters)
        logger.info(f"_prepare_template_params params={params}")

        # 格式化套餐列表
        if "data" in params and isinstance(params["data"], list):
            params["package_list"] = self.formatter.format_package_list(params["data"])

        # 确保所有参数都是字符串（避免format错误）
        for key, value in params.items():
            if value is None:
                params[key] = ""
            elif not isinstance(value, str):
                params[key] = str(value)

        return params

    def _generate_from_llm(self, action: Action, state: DialogState) -> str:
        """
        使用LLM生成

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 生成的文本
        """
        # 构建提示
        user_prompt = self._build_llm_prompt(action, state)

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": self.NLG_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            text = response.choices[0].message.content.strip()
            logger.debug(f"[NLG] LLM生成成功")
            return text

        except Exception as e:
            logger.error(f"[NLG] LLM生成失败: {e}")
            # 降级到模板
            return self._generate_from_template(action, state)

    def _build_llm_prompt(self, action: Action, state: DialogState) -> str:
        """
        构建LLM提示

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 提示文本
        """
        action_type = action.action_type.value if isinstance(action.action_type, ActionType) else action.action_type

        prompt = f"""根据以下信息生成客服回复:

【动作类型】{action_type}
【业务意图】{action.intent}
【对话轮次】{state.turn_count}

【数据内容】
{json.dumps(action.parameters, ensure_ascii=False, indent=2)}

请生成自然、专业的客服回复:"""

        return prompt

    def _generate_hybrid(self, action: Action, state: DialogState) -> str:
        """
        混合生成

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 生成的文本
        """
        # 基础模板
        base_response = self._generate_from_template(action, state)

        # LLM增强（添加推荐或建议）
        if action.parameters.get("should_recommend"):
            enhancement = self._generate_enhancement(action, state)
            return f"{base_response}\n\n{enhancement}"

        return base_response

    def _generate_enhancement(self, action: Action, state: DialogState) -> str:
        """
        生成增强内容（推荐/建议）

        Args:
            action: 系统动作
            state: 对话状态

        Returns:
            str: 增强内容
        """
        prompt = f"""基于用户查询结果，生成个性化推荐:

【查询结果】{action.parameters.get('count', 0)}个套餐
【用户特征】
- 价格预算: {state.slots.get('price_max', '未知')}元
- 流量需求: {state.slots.get('data_min', '未知')}GB

生成一句推荐话术（30字以内）:"""

        try:
            response = self.llm_client.chat.completions.create(
                model=self.llm_model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.8,
                max_tokens=100
            )
            return response.choices[0].message.content.strip()
        except:
            return "根据您的需求，建议选择性价比高的套餐"

    def _fallback_response(self, action: Action) -> str:
        """
        降级响应

        Args:
            action: 系统动作

        Returns:
            str: 降级文本
        """
        fallback_messages = {
            "REQUEST": "请提供相关信息",
            "INFORM": "为您查询到相关信息",
            "CONFIRM": "请确认您的操作",
            "APOLOGIZE": "抱歉，遇到了一些问题",
            "RECOMMEND": "为您推荐合适的套餐",
            "EXECUTE": "正在为您处理",
            "CLARIFY": "请问您的具体需求是什么？",
            "CLOSE": "还有什么可以帮您的吗？"
        }

        action_type = action.action_type.value if isinstance(action.action_type, ActionType) else action.action_type
        return fallback_messages.get(action_type, "处理完成")