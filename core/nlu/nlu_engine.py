"""
NLU引擎核心实现
"""
import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List

from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam, \
    ChatCompletionAssistantMessageParam

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

    def _build_messages(self, user_input: str, context: Dict) -> List[Any]:
        """构建消息列表 - 只包含必要的历史"""
        message_dicts = [
            {"role": "system", "content": SYSTEM_PROMPT},
        ]

        # 获取历史消息
        history_messages = context.get("history", [])

        # 只添加最近的assistant消息作为上下文
        # 不包含之前的user消息，避免混淆
        if history_messages:
            # 找到最近的assistant消息
            for msg in reversed(history_messages[-4:]):  # 只看最近4条
                if msg.get("role") == "user":
                    # 添加最近的assistant回复作为上下文
                    simplified_content = msg["content"][:100] if len(msg["content"]) > 100 else msg["content"]
                    message_dicts.append({
                        "role": "assistant",
                        "content": simplified_content
                    })
                    break

        # 添加当前用户输入
        message_dicts.append({"role": "user", "content": user_input})

        logger.debug(f"构建的消息: {[f'{m['role']}: {m['content'][:30]}...' for m in message_dicts]}")

        # 转换为OpenAI消息参数
        converted_messages = []
        for msg in message_dicts:
            converted_messages.append(self._convert_to_message_param(msg))

        return converted_messages


    def _convert_to_message_param(self, message_dict: Dict) -> Any:
        """将字典消息转换为OpenAI消息参数"""
        role = message_dict["role"]
        content = message_dict.get("content", "")

        if role == "system":
            return ChatCompletionSystemMessageParam(role="system", content=content)
        elif role == "user":
            return ChatCompletionUserMessageParam(role="user", content=content)
        elif role == "assistant":
            return ChatCompletionAssistantMessageParam(role="assistant", content=content)
        else:
            # 其他角色默认作为用户消息处理
            return ChatCompletionUserMessageParam(role="user", content=content)

    def _parse_response(self, response, context: Dict, user_input: str = "") -> NLUResult:
        """解析响应 - 改进版"""
        logger.info(f"解析响应={response}")
        logger.info(
            f"解析响应: tool_calls数量={len(response.choices[0].message.tool_calls) if response.choices[0].message.tool_calls else 0}")
        message = response.choices[0].message

        if message.tool_calls:
            # 处理多个tool_calls的情况
            if len(message.tool_calls) > 1:
                logger.warning(f"⚠️ 收到多个tool_calls: {[tc.function.name for tc in message.tool_calls]}")

                # 选择最相关的tool
                tool_call = self._select_most_relevant_tool(
                    message.tool_calls,
                    context,
                    user_input
                )
                logger.info(f"✓ 选择了最相关的tool: {tool_call.function.name}")
            else:
                tool_call = message.tool_calls[0]

            function_name = tool_call.function.name

            try:
                parameters = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                parameters = {}

            # 验证参数
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

        # 没有tool_calls，返回聊天意图
        return NLUResult(
            intent="chat",
            confidence=0.7,
            raw_response=message.content,
            clarification_message=message.content
        )

    def _select_most_relevant_tool(self, tool_calls, context: Dict, user_input: str):
        """选择最相关的tool_call"""

        # 意图关键词映射（基于你的函数定义）
        INTENT_KEYWORDS = {
            "query_packages": ["套餐", "推荐", "价格", "便宜", "元以内", "元以上", "资费"],
            "query_current_package": ["我的套餐", "当前套餐", "现在用的"],
            "query_usage": ["余量", "剩余", "用了", "还有", "流量使用", "话费", "余额", "消费"],
            "change_package": ["办理", "换", "更换", "变更", "改成", "升级"],
            "query_package_detail": ["详情", "详细", "具体", "介绍"],
            "business_consultation": ["怎么办", "流程", "规则", "优惠", "活动"]
        }

        scores = {}
        user_input_lower = user_input.lower()

        for tool_call in tool_calls:
            function_name = tool_call.function.name
            score = 0

            # 1. 关键词匹配（最重要）
            if function_name in INTENT_KEYWORDS:
                for keyword in INTENT_KEYWORDS[function_name]:
                    if keyword in user_input:
                        score += 20  # 直接匹配权重最高
                        logger.debug(f"  {function_name} 匹配关键词: {keyword} (+20)")

            # 2. 避免重复上一轮意图（除非明确需要）
            previous_intent = context.get("current_intent")
            if previous_intent and function_name == previous_intent:
                # 如果用户输入中没有明确指向该意图的关键词，降低分数
                has_explicit_keyword = any(
                    kw in user_input for kw in INTENT_KEYWORDS.get(function_name, [])
                )
                if not has_explicit_keyword:
                    score -= 10
                    logger.debug(f"  {function_name} 与上轮重复且无明确关键词 (-10)")

            # 3. 参数完整性加分
            try:
                params = json.loads(tool_call.function.arguments)
                if params:
                    score += len(params) * 2
                    logger.debug(f"  {function_name} 有{len(params)}个参数 (+{len(params) * 2})")
            except:
                pass

            scores[tool_call] = score
            logger.info(f"Tool '{function_name}' 最终得分: {score}")

        # 返回得分最高的
        best_tool = max(scores.keys(), key=lambda x: scores[x])
        return best_tool

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
        """更新会话 - 确保记录assistant回复"""
        # 记录用户输入
        context["history"].append({"role": "user", "content": user_input})

        # ⭐ 关键：总是记录assistant回复，即使没有clarification_message
        if result.clarification_message:
            assistant_content = result.clarification_message[:200]
        elif result.function_name:
            # 生成一个简单的确认消息
            intent_descriptions = {
                "query_packages": "正在查询套餐信息",
                "query_usage": "正在查询使用情况",
                "query_current_package": "正在查询您的当前套餐",
                "change_package": "正在为您办理套餐变更",
            }
            assistant_content = intent_descriptions.get(
                result.function_name,
                f"正在处理您的请求"
            )
        else:
            assistant_content = "好的，我来帮您处理"

        # 记录assistant回复
        context["history"].append({
            "role": "assistant",
            "content": assistant_content
        })

        # 意图切换时清理槽位
        if result.intent != context.get("current_intent"):
            logger.info(f"[{session_id}] 意图切换: {context.get('current_intent')} -> {result.intent}")
            phone = context["slot_values"].get("phone") or context.get("user_phone")
            context["slot_values"] = {}
            if phone:
                context["slot_values"]["phone"] = phone

        # 更新状态
        context["current_intent"] = result.intent
        if result.parameters:
            context["slot_values"].update(result.parameters)

        # 限制历史长度
        if len(context["history"]) > 8:
            context["history"] = context["history"][-8:]