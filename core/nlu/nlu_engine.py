"""
NLU引擎核心实现
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam

from config import settings, SYSTEM_PROMPT, SLOT_QUESTIONS
from utils import logger
# 改为从当前包直接导入，而不是从core包导入
from .function_definitions import FUNCTION_DEFINITIONS, get_required_params


@dataclass
class NLUResult:
    """NLU解析结果"""
    intent: str
    function_name: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    requires_clarification: bool = False
    clarification_message: Optional[str] = None
    missing_slots: List[str] = field(default_factory=list)
    raw_response: Optional[str] = None


class NLUEngine:
    """NLU引擎 - 支持DeepSeek"""

    def __init__(self):
        """初始化NLU引擎"""
        self.provider = settings.LLM_PROVIDER

        # 导入OpenAI SDK（DeepSeek兼容OpenAI接口）
        from openai import OpenAI

        if self.provider == "deepseek":
            # 配置DeepSeek
            if not settings.DEEPSEEK_API_KEY:
                raise ValueError("未配置DEEPSEEK_API_KEY，请检查.env文件")

            self.client = OpenAI(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL
            )
            self.model = settings.DEEPSEEK_MODEL
            logger.info(f"✓ NLU引擎初始化成功: DeepSeek ({self.model})")

        elif self.provider == "openai":
            if not settings.OPENAI_API_KEY:
                raise ValueError("未配置OPENAI_API_KEY")

            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
            self.model = settings.OPENAI_MODEL
            logger.info(f"✓ NLU引擎初始化成功: OpenAI ({self.model})")

        else:
            raise ValueError(f"不支持的LLM提供商: {self.provider}")

        self.sessions = {}

    def understand(self,
                   user_input: str,
                   session_id: str,
                   user_phone: Optional[str] = None) -> NLUResult:
        """理解用户输入"""
        logger.info(f"[{session_id}] 开始NLU理解: {user_input}")

        try:
            # 1. 预处理
            processed_text = self._preprocess(user_input)
            logger.debug(f"[{session_id}] 预处理后: {processed_text}")

            # 2. 获取上下文
            context = self._get_session_context(session_id)
            if user_phone:
                context["user_phone"] = user_phone

            # 3. 构建消息
            messages = self._build_messages(processed_text, context)
            logger.info(f"请求模型message={messages}")
            # 4. 调用DeepSeek API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=FUNCTION_DEFINITIONS,
                tool_choice="required",  # ⭐ 改为auto
                temperature=0.2,  # 降低随机性
                top_p=0.9,
                frequency_penalty=0.2  # 避免重复
            )

            # 5. 解析响应
            nlu_result = self._parse_response(response, context, processed_text)

            # 6. 更新会话
            self._update_session(session_id, user_input, nlu_result, context)

            logger.info(f"[{session_id}] NLU完成: intent={nlu_result.intent}")
            return nlu_result

        except Exception as e:
            logger.error(f"[{session_id}] NLU异常: {str(e)}")
            return NLUResult(
                intent="error",
                confidence=0.0,
                requires_clarification=True,
                clarification_message=f"抱歉,处理出现问题: {str(e)}"
            )

    def _preprocess(self, text: str) -> str:
        """文本预处理"""
        text = re.sub(r'\s+', ' ', text).strip()
        text = text.replace('一百', '100').replace('两百', '200')
        text = text.replace('块', '元')
        return text

    def _get_session_context(self, session_id: str) -> Dict:
        """获取会话上下文"""
        if session_id not in self.sessions:
            self.sessions[session_id] = {
                "history": [],
                "current_intent": None,
                "slot_values": {},
                "user_phone": None,
                "created_at": datetime.now()
            }
        return self.sessions[session_id]

    # ========== 3️⃣ 改进消息构建（精准上下文版）==========
    def _build_messages(self, user_input: str, context: Dict) -> List[Any]:
        """
        构建消息 - 精准上下文传递

        策略：
        1. 基础：System Prompt + 当前输入
        2. 槽位填充场景：添加精简的任务上下文
        3. 避免：完整历史对话（避免参数污染）
        """
        messages = []

        # 1. 动态System Prompt
        system_content = self._build_dynamic_system_prompt(context)
        messages.append(
            ChatCompletionSystemMessageParam(
                role="system",
                content=system_content
            )
        )

        # 2. 判断是否在槽位填充状态
        is_slot_filling = self._is_slot_filling_state(context)

        if is_slot_filling:
            # 场景A: 槽位填充 - 添加精简上下文
            task_context = self._build_task_context(context)
            messages.append(
                ChatCompletionUserMessageParam(
                    role="user",
                    content=task_context
                )
            )

        # 3. 当前用户输入
        messages.append(
            ChatCompletionUserMessageParam(
                role="user",
                content=user_input
            )
        )

        return messages

    def _is_slot_filling_state(self, context: Dict) -> bool:
        """
        判断是否处于槽位填充状态

        条件：
        1. 有当前意图
        2. 有缺失的必填槽位
        3. 最近一轮是系统询问
        """
        if not context.get("current_intent"):
            return False

        # 检查是否有等待填充的槽位
        if context.get("waiting_for_slot"):
            return True

        # 检查历史：最后一条是否是系统询问
        history = context.get("history", [])
        if history and history[-1].get("role") == "assistant":
            last_msg = history[-1].get("content", "")
            # 如果包含"请问"、"请提供"等询问词
            if any(word in last_msg for word in ["请问", "请提供", "请告诉", "您的"]):
                return True

        return False

    def _build_task_context(self, context: Dict) -> str:
        """
        构建任务上下文（槽位填充场景）

        输出示例：
        "用户正在办理畅游套餐，当前需要提供手机号"
        """
        intent = context.get("current_intent")
        waiting_slot = context.get("waiting_for_slot")
        known_params = context.get("slot_values", {})

        # 意图描述映射
        intent_desc = {
            "change_package": "办理套餐",
            "query_current_package": "查询当前套餐",
            "query_usage": "查询使用情况",
            "query_packages": "查询套餐"
        }

        # 槽位描述映射
        slot_desc = {
            "phone": "手机号",
            "new_package_name": "套餐名称",
            "package_name": "套餐名称"
        }

        task_desc = intent_desc.get(intent, "处理请求")

        # 构建上下文
        parts = [f"用户正在{task_desc}"]

        # 添加已知参数
        if known_params:
            known_desc = []
            for key, value in known_params.items():
                if key != "phone":  # phone不在这里暴露
                    known_desc.append(f"{slot_desc.get(key, key)}: {value}")
            if known_desc:
                parts.append(f"已知信息: {', '.join(known_desc)}")

        # 添加等待填充的槽位
        if waiting_slot:
            parts.append(f"当前等待用户提供{slot_desc.get(waiting_slot, waiting_slot)}")

        return "。".join(parts) + "。"

    def _build_dynamic_system_prompt(self, context: Dict) -> str:
        """
        构建动态System Prompt

        根据是否在槽位填充状态，调整提示词
        """
        base_prompt = SYSTEM_PROMPT

        if self._is_slot_filling_state(context):
            # 槽位填充场景：添加特殊指示
            slot_filling_instruction = f"""

【当前状态】槽位填充模式
- 用户的输入可能是在回答之前的问题
- 优先判断输入是否是缺失槽位的值
- 如果是槽位值（如手机号、套餐名），继续当前意图
- 如果是全新问题，切换到新意图

【判断规则】
- 11位数字 → 可能是手机号，用于当前意图
- 套餐名称 → 用于当前意图  
- 明确新问题关键词（"查询"、"我要"等）→ 新意图
"""
            return base_prompt + slot_filling_instruction

        return base_prompt

    # ========== 4️⃣ 改进响应解析（增加槽位填充识别）==========
    def _parse_response(self, response, context: Dict, user_input: str):
        """改进的响应解析 - 支持槽位填充场景"""
        logger.info(f"NLU 模型返回={response},context={context},user_input={user_input}")
        message = response.choices[0].message

        # 🔥 特殊处理：槽位填充场景
        if context.get("waiting_for_slot"):
            return self._parse_slot_filling_response(
                message,
                context,
                user_input
            )

        # 处理tool_calls
        if message.tool_calls:
            tool_calls = message.tool_calls

            # 关键：处理多个tool_calls
            if len(tool_calls) > 1:
                tool_call = self._select_best_tool(
                    tool_calls,
                    user_input,
                    context
                )
            else:
                tool_call = tool_calls[0]

            function_name = tool_call.function.name

            try:
                parameters = json.loads(tool_call.function.arguments)
            except:
                parameters = {}

            # 关键：过滤无效参数
            parameters = self._filter_invalid_params(
                function_name,
                parameters,
                user_input
            )

            # 验证必填参数
            missing_slots = self._validate_parameters(
                function_name,
                parameters,
                context
            )

            if missing_slots:
                return NLUResult(
                    intent=function_name,
                    function_name=function_name,
                    parameters=parameters,
                    requires_clarification=True,
                    clarification_message=self._get_slot_question(missing_slots[0]),
                    missing_slots=missing_slots
                )

            return NLUResult(
                intent=function_name,
                function_name=function_name,
                parameters=parameters,
                confidence=0.9
            )

        # 纯文本回复
        return NLUResult(
            intent="chat",
            raw_response=message.content
        )

    def _parse_slot_filling_response(self, message, context: Dict, user_input: str):
        """
        槽位填充场景的特殊解析

        策略：
        1. 检查用户输入是否匹配等待的槽位类型
        2. 如果匹配，继续当前意图并填充槽位
        3. 如果不匹配，按正常流程处理（可能是新意图）
        """
        waiting_slot = context["waiting_for_slot"]
        current_intent = context["current_intent"]

        # 尝试从用户输入直接识别槽位值
        slot_value = self._extract_slot_value(user_input, waiting_slot)

        if slot_value:
            # 成功识别槽位值，继续当前意图
            parameters = dict(context.get("slot_values", {}))
            parameters[waiting_slot] = slot_value

            # 重新验证必填参数
            missing_slots = self._validate_parameters(
                current_intent,
                parameters,
                context
            )

            if missing_slots:
                # 还有其他缺失槽位
                return NLUResult(
                    intent=current_intent,
                    function_name=current_intent,
                    parameters=parameters,
                    requires_clarification=True,
                    clarification_message=self._get_slot_question(missing_slots[0]),
                    missing_slots=missing_slots
                )
            else:
                # 所有槽位已填充
                return NLUResult(
                    intent=current_intent,
                    function_name=current_intent,
                    parameters=parameters,
                    confidence=0.9
                )

        # 无法识别为槽位值，可能是新意图
        # 检查LLM返回
        if message.tool_calls:
            # 按正常流程处理（可能切换了意图）
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name

            try:
                parameters = json.loads(tool_call.function.arguments)
            except:
                parameters = {}

            return NLUResult(
                intent=function_name,
                function_name=function_name,
                parameters=parameters,
                confidence=0.8
            )

        # 无法解析，返回chat
        return NLUResult(
            intent="chat",
            raw_response=message.content or "抱歉，没有理解您的意思"
        )

    def _extract_slot_value(self, user_input: str, slot_name: str):
        """
        从用户输入中提取槽位值

        支持的槽位类型：
        - phone: 11位数字
        - package_name: 套餐名称
        - new_package_name: 套餐名称
        """
        import re

        # 手机号识别
        if slot_name in ["phone"]:
            # 提取11位数字
            phone_match = re.search(r'1[3-9]\d{9}', user_input)
            if phone_match:
                return phone_match.group()

        # 套餐名称识别
        if slot_name in ["package_name", "new_package_name"]:
            package_names = ["经济套餐", "畅游套餐", "无限套餐", "校园套餐"]
            for name in package_names:
                if name in user_input:
                    return name

        return None

    # ========== 5️⃣ 新增：智能tool选择 ==========
    def _select_best_tool(self, tool_calls, user_input: str, context: Dict):
        """
        从多个tool_calls中选择最佳的

        策略：
        1. 优先选择参数最完整的
        2. 避免重复上一轮的意图
        3. 基于关键词匹配
        """
        scores = {}

        for tool in tool_calls:
            score = 0
            function_name = tool.function.name

            # 1. 参数完整性加分
            try:
                params = json.loads(tool.function.arguments)
                score += len(params) * 10
            except:
                params = {}

            # 2. 避免重复上一轮意图
            if context.get("current_intent") == function_name:
                score -= 20

            # 3. 关键词匹配
            keywords = {
                "query_packages": ["套餐", "推荐", "价格"],
                "query_usage": ["用了", "剩余", "余额", "流量使用"],
                "query_current_package": ["我的", "当前"]
            }

            for keyword in keywords.get(function_name, []):
                if keyword in user_input:
                    score += 15

            scores[tool] = score

        # 返回得分最高的
        return max(scores.keys(), key=lambda t: scores[t])

        # ========== 6️⃣ 新增：参数过滤 ==========

    def _filter_invalid_params(self, function_name: str,
                               parameters: Dict,
                               user_input: str) -> Dict:
        """
        过滤无效参数

        规则：
        1. 如果参数值在当前用户输入中不存在，删除
        2. 特殊处理：phone、数字等
        """
        filtered = {}

        for key, value in parameters.items():
            # 规则1: phone必须是11位数字
            if key == "phone":
                if isinstance(value, str) and len(value) == 11 and value.isdigit():
                    filtered[key] = value
                continue

            # 规则2: 数字参数验证（价格、流量）
            if key in ["price_min", "price_max", "data_min", "data_max"]:
                # 检查用户输入中是否有相关数字
                if str(value) in user_input or self._number_in_text(value, user_input):
                    filtered[key] = value
                continue

            # 规则3: 其他参数直接保留
            filtered[key] = value

        return filtered

    def _number_in_text(self, number: int, text: str) -> bool:
        """检查数字是否在文本中（支持中文数字）"""
        # 简单实现
        return str(number) in text or self._chinese_to_num(text, number)

    def _chinese_to_num(self, text: str, target: int) -> bool:
        """检查文本中的中文数字"""
        mapping = {
            "一百": 100, "二百": 200, "三百": 300,
            "五十": 50, "六十": 60, "八十": 80,
        }
        for chinese, num in mapping.items():
            if chinese in text and num == target:
                return True
        return False



    def _validate_parameters(self, function_name: str, parameters: Dict, context: Dict) -> List[str]:
        """验证参数"""
        missing = []
        required = get_required_params(function_name)

        for param in required:
            if param not in parameters or not parameters[param]:
                if param == "phone" and context.get("user_phone"):
                    parameters[param] = context["user_phone"]
                elif param in context.get("slot_values", {}):
                    parameters[param] = context["slot_values"][param]
                else:
                    missing.append(param)

        return missing

    def _get_slot_question(self, slot_name: str) -> str:
        """获取槽位询问话术"""
        return SLOT_QUESTIONS.get(slot_name, f"请提供{slot_name}信息")

    # ========== 7️⃣ 改进会话更新（增加槽位跟踪）==========
    def _update_session(self, session_id: str, user_input: str,
                        result, context: Dict):
        """
        改进的会话更新

        新增：
        1. 记录waiting_for_slot状态
        2. 记录上一轮的系统回复（用于判断槽位填充）
        """
        # 记录用户输入
        context["history"].append({
            "role": "user",
            "content": user_input[:100]
        })

        # 意图切换处理
        if result.intent != context.get("current_intent"):
            # 清空waiting_for_slot
            context["waiting_for_slot"] = None

            # 保留用户信息
            phone = context.get("user_phone") or context["slot_values"].get("phone")
            context["slot_values"] = {}
            if phone:
                context["slot_values"]["phone"] = phone

        # 更新当前意图
        context["current_intent"] = result.intent

        # 更新槽位
        if result.parameters:
            context["slot_values"].update(result.parameters)

        # 🔥 关键：如果需要澄清，记录等待的槽位
        if result.requires_clarification and result.missing_slots:
            context["waiting_for_slot"] = result.missing_slots[0]

            # 记录系统的询问（用于下轮判断）
            context["history"].append({
                "role": "assistant",
                "content": result.clarification_message[:100]
            })
        else:
            # 槽位已填充完成，清空等待状态
            context["waiting_for_slot"] = None

        # 限制历史长度（只保留最近4条：2轮对话）
        if len(context["history"]) > 4:
            context["history"] = context["history"][-4:]
