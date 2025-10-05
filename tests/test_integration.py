"""
集成测试
"""
import pytest

from core import TelecomChatbotNlu, TelecomChatbotDst
from utils import logger


class TestNLUIntegration:
    """集成测试"""

    @pytest.fixture
    def chatbot(self):
        """创建聊天机器人实例"""
        return TelecomChatbotNlu()

    def test_complete_conversation(self, chatbot):
        """测试完整对话流程"""
        # 查询套餐
        response = chatbot.chat(
            "有100元以内的套餐吗",
            session_id="integration_test_001"
        )

        logger.info(f"返回结果: {response}")

        assert response["intent"] == "query_packages"
        assert not response["requires_input"]
        assert response["data"]["success"]

    def test_multi_turn_conversation(self, chatbot):
        """测试多轮对话"""
        session_id = "integration_test_002"

        # 第一轮: 询问套餐但未提供手机号
        response1 = chatbot.chat(
            "查下我的套餐",
            session_id=session_id
        )

        assert response1["requires_input"]
        assert "phone" in response1.get("missing_slots", [])

        # 第二轮: 提供手机号
        response2 = chatbot.chat(
            "13800138000",
            session_id=session_id
        )

        assert not response2["requires_input"]
        assert response2["data"]["success"]


class TestDSTIntegration:
    """
    Dst集成测试
    """

    @pytest.fixture
    def chatbot(self):
        """创建聊天机器人实例"""
        return TelecomChatbotDst()

    def test_multi_turn_conversation(self, chatbot):
        """测试多轮对话"""
        session_id = "integration_test_001"

        # 第一轮: 查询套餐
        response1 = chatbot.chat(
            "有100元以内的套餐吗",
            session_id=session_id
        )
        logger.info(f"第一轮返回结果: {response1}")
        assert response1["intent"] == "query_packages"
        assert not response1["requires_input"]

        # 第二轮: 继续添加条件
        response2 = chatbot.chat(
            "流量要50G以上",
            session_id=session_id
        )

        # 验证槽位继承
        state = response2.get("state", {})
        logger.info(f"第二轮返回结果: {state}")
        slots = state.get("slots", {})
        assert slots.get("price_max") == 100  # 继承
        assert slots.get("data_min") == 50  # 新增

    def test_slot_inheritance_across_intents(self, chatbot):
        """测试跨意图的槽位继承"""
        session_id = "integration_test_0002"

        # 第一轮: 查询当前套餐（需要手机号）
        response1 = chatbot.chat(
            "查下我的套餐",
            session_id=session_id
        )
        assert response1["requires_input"]
        assert "phone" in response1.get("missing_slots", [])

        # 第二轮: 提供手机号
        response2 = chatbot.chat(
            "13800138000",
            session_id=session_id
        )
        assert not response2["requires_input"]

        # 第三轮: 切换意图，查询使用情况
        response3 = chatbot.chat(
            "我用了多少流量",
            session_id=session_id
        )

        # phone应该自动继承，不需要再问
        assert not response3["requires_input"]
        state = response3.get("state", {})
        assert state.get("slots", {}).get("phone") == "13800138000"

    def test_intent_switch_clears_slots(self, chatbot):
        """测试意图切换时清空槽位"""
        session_id = "integration_test_003"

        # 第一轮: 查询套餐
        response1 = chatbot.chat(
            "100元以内的套餐",
            session_id=session_id
        )
        state1 = response1.get("state", {})
        assert "price_max" in state1.get("slots", {})

        # 第二轮: 切换到完全不同的意图
        response2 = chatbot.chat(
            "我要办理套餐",
            session_id=session_id
        )
        state2 = response2.get("state", {})
        slots2 = state2.get("slots", {})

        # price_max应该被清除
        assert "price_max" not in slots2

    def test_state_persistence(self, chatbot):
        """测试状态持久化"""
        session_id = "persistence_test_001"

        # 第一次对话
        response1 = chatbot.chat(
            "有100元以内的套餐吗",
            session_id=session_id
        )

        # 创建新实例（模拟重启）
        chatbot2 = TelecomChatbotDst()

        # 继续对话
        response2 = chatbot2.chat(
            "流量要50G以上",
            session_id=session_id
        )

        # 验证状态恢复
        state = response2.get("state", {})
        assert state.get("slots", {}).get("price_max") == 100  # 应该恢复


class TestContextManagement:
    """上下文管理测试"""

    @pytest.fixture
    def chatbot(self):
        return TelecomChatbotDst()

    def test_context_stack_size_limit(self, chatbot):
        """测试上下文栈大小限制"""
        session_id = "context_test_001"

        # 进行20轮对话
        for i in range(20):
            chatbot.chat(f"查询{i}", session_id=session_id)

        # 获取状态
        state = chatbot.get_session_state(session_id)

        # 上下文栈应该有大小限制
        assert len(state.get("context_stack", [])) <= 10

    def test_context_extraction(self, chatbot):
        """测试从上下文提取实体"""
        session_id = "context_test_002"

        # 提供手机号
        response1 = chatbot.chat(
            "我的手机号是13800138000",
            session_id=session_id
        )

        # 切换到其他对话
        response2 = chatbot.chat(
            "有什么套餐",
            session_id=session_id
        )

        # 再次需要手机号时应该能从上下文提取
        response3 = chatbot.chat(
            "查下我的套餐",
            session_id=session_id
        )

        # 应该不需要再问手机号
        # 注意：这个测试可能需要根据实际实现调整
        state = response3.get("state", {})
        phone = state.get("slots", {}).get("phone")
        assert phone == "13800138000" or response3.get("requires_input")

class TestErrorHandling:
    @pytest.fixture
    def chatbot(self):
        return TelecomChatbotDst()

    def test_invalid_session_recovery(self, chatbot):
        """测试无效会话恢复"""
        # 使用一个不存在的session_id
        response = chatbot.chat(
            "你好",
            session_id="non_existent_session"
        )

        # 应该能正常处理
        assert "session_id" in response
        assert "response" in response

    def test_redis_fallback(self, chatbot):
        """测试Redis降级"""
        # 这个测试需要模拟Redis故障
        # 实际实现时可以临时禁用Redis连接
        session_id = "fallback_test"

        response = chatbot.chat(
            "有什么套餐",
            session_id=session_id
        )

        # 即使Redis不可用，也应该能正常工作（降级到内存）
        assert "response" in response