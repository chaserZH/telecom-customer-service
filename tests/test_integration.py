"""
集成测试
"""
import pytest

from core import TelecomChatbotNlu
from utils import logger


class TestIntegration:
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