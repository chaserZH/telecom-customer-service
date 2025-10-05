# -*- coding: utf-8 -*-
"""
第二阶段完整对话系统 - 增加DST支持
"""
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from core import NLUEngine
from core.dst import DialogStateTracker
from executor.db_executor import DatabaseExecutor
from utils.logger import logger


class TelecomChatbotDst:
    """电信客服对话系统 - 第二阶段版本（含DST）"""

    def __init__(self):
        """初始化对话系统"""
        self.nlu = NLUEngine()
        self.dst = DialogStateTracker()  # ⭐ 新增DST
        self.db_executor = DatabaseExecutor()
        logger.info("第二阶段对话系统初始化完成（含DST支持）")

    def chat(self,
             user_input: str,
             session_id: Optional[str] = None,
             user_phone: Optional[str] = None) -> Dict[str, Any]:
        """
        处理用户输入,返回响应

        Args:
            user_input: 用户输入文本
            session_id: 会话ID(可选,自动生成)
            user_phone: 用户手机号(可选)

        Returns:
            响应字典
        """
        start_time = datetime.now()

        # 生成会话ID
        if not session_id:
            session_id = str(uuid.uuid4())

        logger.info(f"[{session_id}] 收到用户输入: {user_input}")

        try:
            # 步骤1: NLU理解（不传递session_id，避免与DST冲突）
            nlu_result = self.nlu.understand(user_input, session_id, user_phone)
            nlu_result.raw_input = user_input  # 保存原始输入

            # 步骤2: DST状态跟踪 ⭐ 核心新增
            dialog_state = self.dst.track(session_id, nlu_result)

            # 步骤3: 如果需要澄清,直接返回
            if dialog_state.needs_clarification:
                response = {
                    "session_id": session_id,
                    "response": self._get_clarification_message(dialog_state),
                    "intent": dialog_state.current_intent,
                    "requires_input": True,
                    "missing_slots": dialog_state.missing_slots,
                    "state": dialog_state.to_dict(),
                    "timestamp": datetime.now().isoformat()
                }
                self._log_conversation(session_id, user_input, dialog_state, response, start_time)
                return response

            # 步骤4: 执行Function（使用DST中维护的槽位）
            exec_result = None
            if dialog_state.current_intent:
                exec_result = self.db_executor.execute_function(
                    dialog_state.current_intent,
                    dialog_state.slots  # ⭐ 使用DST维护的槽位
                )

            # 步骤5: 生成自然语言响应
            response_text = self._generate_response(
                dialog_state.current_intent,
                dialog_state.slots,
                exec_result
            )

            # 步骤6: 添加助手回复到历史
            dialog_state.add_turn('assistant', response_text)
            self.dst.state_store.save(session_id, dialog_state)

            response = {
                "session_id": session_id,
                "response": response_text,
                "intent": dialog_state.current_intent,
                "function": dialog_state.current_intent,
                "parameters": dialog_state.slots,
                "data": exec_result,
                "requires_input": False,
                "state": dialog_state.to_dict(),
                "timestamp": datetime.now().isoformat()
            }

            self._log_conversation(session_id, user_input, dialog_state, response, start_time)
            return response

        except Exception as e:
            logger.error(f"[{session_id}] 处理异常: {e}", exc_info=True)
            return {
                "session_id": session_id,
                "response": f"抱歉,系统遇到了问题: {str(e)}",
                "intent": "error",
                "requires_input": False,
                "timestamp": datetime.now().isoformat()
            }

    def _get_clarification_message(self, state) -> str:
        """生成澄清消息"""
        from config.prompts import SLOT_QUESTIONS

        if not state.missing_slots:
            return "请提供更多信息。"

        slot_name = state.missing_slots[0]
        return SLOT_QUESTIONS.get(slot_name, f"请提供{slot_name}信息")

    def _generate_response(self,
                           intent: str,
                           parameters: Dict,
                           exec_result: Optional[Dict]) -> str:
        """生成自然语言响应"""

        # 如果执行失败
        if exec_result and not exec_result.get("success"):
            return f"抱歉,{exec_result.get('error', '处理出现问题')}"

        # 根据不同Function生成不同的响应
        if intent == "query_packages":
            return self._format_packages_response(exec_result)

        elif intent == "query_current_package":
            return self._format_current_package_response(exec_result)

        elif intent == "query_package_detail":
            return self._format_package_detail_response(exec_result)

        elif intent == "change_package":
            return exec_result.get("message", "办理成功")

        elif intent == "query_usage":
            return self._format_usage_response(exec_result)

        elif intent == "business_consultation":
            return exec_result.get("response", "")

        elif intent == "chat":
            return "有什么可以帮您的吗?"

        return "已为您处理完成"

    def _format_packages_response(self, result: Dict) -> str:
        """格式化套餐列表响应"""
        packages = result.get("data", [])

        if not packages:
            return "抱歉,没有找到符合条件的套餐。要不要看看其他套餐?"

        response = f"为您找到 {len(packages)} 个合适的套餐:\n\n"

        for i, pkg in enumerate(packages, 1):
            response += f"【{pkg['name']}】\n"
            response += f"  💰 月费: {pkg['price']}元\n"
            response += f"  📊 流量: {pkg['data_gb']}GB/月\n"
            response += f"  📞 通话: {pkg.get('voice_minutes', 0)}分钟/月\n"
            response += f"  👥 适用: {pkg['target_user']}\n"
            if pkg.get('description'):
                response += f"  📝 {pkg['description']}\n"
            response += "\n"

        response += "如需办理或了解详情,请告诉我套餐名称和您的手机号码。"
        return response

    def _format_current_package_response(self, result: Dict) -> str:
        """格式化当前套餐响应"""
        data = result.get("data", {})

        response = f"📱 您当前使用的是【{data['package_name']}】\n\n"
        response += f"手机号: {data['phone']}\n"
        response += f"套餐内容:\n"
        response += f"  • 流量: {data['data_gb']}GB/月\n"
        response += f"  • 通话: {data.get('voice_minutes', 0)}分钟/月\n"
        response += f"  • 月费: {data['price']}元\n\n"
        response += f"使用情况:\n"
        response += f"  • 本月已用流量: {data['monthly_usage_gb']}GB\n"
        response += f"  • 本月已用通话: {data.get('monthly_usage_minutes', 0)}分钟\n"
        response += f"  • 账户余额: {data['balance']}元\n"

        return response

    def _format_package_detail_response(self, result: Dict) -> str:
        """格式化套餐详情响应"""
        data = result.get("data", {})

        response = f"【{data['name']}】套餐详情\n\n"
        response += f"💰 月费: {data['price']}元\n"
        response += f"📊 每月流量: {data['data_gb']}GB\n"
        response += f"📞 每月通话: {data.get('voice_minutes', 0)}分钟\n"
        response += f"👥 适用人群: {data['target_user']}\n"
        if data.get('description'):
            response += f"\n📝 套餐说明:\n{data['description']}\n"

        response += "\n如需办理,请告诉我您的手机号码。"
        return response

    def _format_usage_response(self, result: Dict) -> str:
        """格式化使用情况响应"""
        response = f"📱 {result['phone']} 的使用情况:\n\n"

        if "monthly_usage_gb" in result:
            response += f"📈 本月已用流量: {result['monthly_usage_gb']}GB\n"
            response += f"📞 本月已用通话: {result.get('monthly_usage_minutes', 0)}分钟\n"

        if "balance" in result:
            response += f"💳 账户余额: {result['balance']}元\n"

        return response

    def _log_conversation(self,
                          session_id: str,
                          user_input: str,
                          dialog_state,
                          response: Dict,
                          start_time: datetime):
        """记录对话日志"""
        execution_time = (datetime.now() - start_time).total_seconds() * 1000

        logger.info(
            f"[{session_id}] 对话完成 | "
            f"意图: {dialog_state.current_intent} | "
            f"轮次: {dialog_state.turn_count} | "
            f"耗时: {execution_time:.0f}ms"
        )

    def get_session_state(self, session_id: str) -> Dict:
        """获取会话状态（用于调试）"""
        state = self.dst.get_state(session_id)
        return state.to_dict()

    def reset_session(self, session_id: str):
        """重置会话"""
        self.dst.reset_state(session_id)
        logger.info(f"重置会话: {session_id}")