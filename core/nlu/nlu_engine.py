"""
NLU引擎核心实现
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from config import settings, SYSTEM_PROMPT, SLOT_QUESTIONS
# 改为从当前包直接导入，而不是从core包导入
from .function_definitions import FUNCTION_DEFINITIONS, get_required_params

from utils import logger


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
        """
        理解用户输入

        Args:
            user_input: 用户输入文本
            session_id: 会话ID
            user_phone: 用户手机号(如果已知)

        Returns:
            NLUResult: NLU解析结果
        """
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

            # 4. 调用DeepSeek API（使用OpenAI SDK格式）
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=FUNCTION_DEFINITIONS,
                tool_choice="auto",
                temperature=0.3
            )

            # 5. 解析响应
            nlu_result = self._parse_response(response, context)

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

    # 在NLU引擎中添加示例（修改 core/nlu/nlu_engine.py）：
    def _build_messages(self, user_input: str, context: Dict) -> List[Dict]:
        """构建消息列表"""
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            # ⭐ 添加few-shot示例
            {"role": "user", "content": "查下我的套餐"},
            {"role": "assistant", "content": "", "tool_calls": [
                {
                    "id": "call_example",
                    "type": "function",
                    "function": {
                        "name": "query_current_package",
                        "arguments": "{}"
                    }
                }
            ]},
            {"role": "user", "content": "有什么套餐"},
            {"role": "assistant", "content": "", "tool_calls": [
                {
                    "id": "call_example2",
                    "type": "function",
                    "function": {
                        "name": "query_packages",
                        "arguments": "{}"
                    }
                }
            ]},
        ]

        # 添加历史消息
        messages.extend(context.get("history", [])[-10:])

        # 添加当前用户输入
        messages.append({"role": "user", "content": user_input})

        return messages

    def _parse_response(self, response, context: Dict) -> NLUResult:
        """解析响应"""
        message = response.choices[0].message

        if message.tool_calls:
            tool_call = message.tool_calls[0]
            function_name = tool_call.function.name

            try:
                parameters = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                parameters = {}

            missing_slots = self._validate_parameters(function_name, parameters, context)

            if missing_slots:
                return NLUResult(
                    intent=function_name,
                    function_name=function_name,
                    parameters=parameters,
                    confidence=0.8,
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

        return NLUResult(
            intent="chat",
            confidence=0.7,
            raw_response=message.content,
            clarification_message=message.content
        )

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

    def _update_session(self, session_id: str, user_input: str,
                        result: NLUResult, context: Dict):
        """更新会话"""
        context["history"].append({"role": "user", "content": user_input})

        if result.clarification_message:
            context["history"].append({
                "role": "assistant",
                "content": result.clarification_message
            })

        context["current_intent"] = result.intent

        if result.parameters:
            context["slot_values"].update(result.parameters)

        if len(context["history"]) > 20:
            context["history"] = context["history"][-20:]