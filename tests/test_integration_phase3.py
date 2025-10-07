"""
第三阶段集成测试
"""
import pytest
from core import TelecomChatbotPolicy
from utils import logger


class TestPhase3Integration:
    """第三阶段集成测试"""

    @pytest.fixture
    def chatbot(self):
        """创建聊天机器人实例"""
        return TelecomChatbotPolicy()

    def test_complete_flow(self, chatbot):
        """测试完整对话流程"""
        session_id = "integration_test_0011"

        # 第1轮：查询套餐
        response1 = chatbot.chat(
            "有100元以内的套餐吗",
            session_id=session_id
        )

        assert response1["intent"] == "query_packages"
        assert response1["action"] == "INFORM"
        assert "套餐" in response1["response"]

    def test_recommendation_flow(self, chatbot):
        """测试推荐流程"""
        session_id = "integration_test_0021"

        response = chatbot.chat(
            "有什么套餐",
            session_id=session_id
        )

        logger.info(f"[{session_id}] 收到返回: {response}")

        assert response["action"] in ["INFORM", "RECOMMEND"]
        assert response["data"] is not None

    def test_confirmation_flow(self, chatbot):
        """测试确认流程"""
        session_id = "integration_test_0035"

        # 第1轮：请求办理
        response1 = chatbot.chat(
            "我要办理畅游套餐",
            session_id=session_id
        )

        logger.info(f"[{session_id}] 收到返回1: {response1}")
        # 应该请求手机号或确认
        assert response1["action"] in ["REQUEST", "CONFIRM"]

        # 第2轮：提供手机号
        if response1["action"] == "REQUEST":
            response2 = chatbot.chat(
                "13800138000",
                session_id=session_id
            )

            logger.info(f"[{session_id}] 收到返回: {response2}")
            # 应该确认
            assert response2["action"] == "CONFIRM"
            assert "确认" in response2["response"]

    def test_error_handling(self, chatbot):
        """测试错误处理"""
        session_id = "integration_test_004"

        # 查询不存在的手机号
        response = chatbot.chat(
            "查询123的套餐",
            session_id=session_id
        )

        # 应该有错误提示
        assert "response" in response

    def test_multi_turn_conversation(self, chatbot):
        """测试多轮对话"""
        session_id = "integration_test_0057"

        # 第1轮
        response1 = chatbot.chat("有便宜的套餐吗", session_id=session_id)
        assert "套餐" in response1["response"]

        # 第2轮：继续筛选
        response2 = chatbot.chat("流量要50G以上", session_id=session_id)
        assert response2["data"]["count"] == 3

        # 第3轮：切换意图
        response3 = chatbot.chat("查我的套餐", session_id=session_id)
        logger.info(f"[{session_id}] 收到返回: {response3}")
        assert response3["intent"] == "query_current_package"

    def test_cache_effectiveness(self, chatbot):
        """测试缓存效果"""
        session_id1 = "cache_test_001"
        session_id2 = "cache_test_002"

        # 第一次请求（未命中缓存）
        response1 = chatbot.chat(
            "请提供手机号",
            session_id=session_id1
        )

        # 第二次相同请求（可能命中缓存）
        response2 = chatbot.chat(
            "请提供手机号",
            session_id=session_id2
        )

        # 验证响应存在
        assert "response" in response1
        assert "response" in response2

        # 获取缓存统计
        stats = chatbot.get_cache_stats()
        assert "size" in stats

    def test_confirm_conversation(self, chatbot):

        session_id = "test_001"

        # 测试1：办理套餐（应该要求确认）
        print("=== 测试1：办理套餐 ===")
        result1 = chatbot.chat("我要办理经济套餐，手机号13800138000", session_id=session_id)
        print(f"响应: {result1['response']}")
        print(f"Action: {result1['action']}")
        print(f"待确认: {result1['state']['pending_confirmation']}")
        # 预期：返回确认提示，数据库未执行

        # 测试2：用户确认（应该执行业务）
        print("\n=== 测试2：用户确认 ===")
        result2 = chatbot.chat("确认", session_id=session_id)
        print(f"响应: {result2['response']}")
        print(f"Action: {result2['action']}")
        print(f"数据: {result2.get('data', {})}")
        # 预期：执行业务，返回成功消息

        # 测试3：取消操作
        print("\n=== 测试3：取消操作 ===")
        session_id2 = "test_002"
        chatbot.chat("我要办理无限套餐，手机号13900139000", session_id=session_id2)
        result3 = chatbot.chat("算了不办了", session_id=session_id2)
        print(f"响应: {result3['response']}")