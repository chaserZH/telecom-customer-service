"""
测试用户取消/确认转移
"""
import time

import pytest
from core import TelecomChatbotPolicy
from utils import logger


class TestPhase3Confirm:


    @pytest.fixture
    def chatbot(self):
        """创建聊天机器人实例"""
        return TelecomChatbotPolicy()

    #场景1：转移到相关话题（应保留）
    def test_complete_flow(self, chatbot):
        session_id = "test_related2"

        # 第1步：发起办理
        r1 = chatbot.chat("办理经济套餐，13800138000", session_id=session_id)
        print(f"步骤1: {r1['response']}")
        print(f"待确认: {r1['state']['pending_confirmation']}")  # True

        # 第2步：查询套餐详情（相关话题）
        r2 = chatbot.chat("经济套餐有什么内容？", session_id=session_id)
        print(f"步骤2: {r2['response']}")
        print(f"待确认: {r2['state']['pending_confirmation']}")  # True ✅ 保留

        # 第3步：确认
        r3 = chatbot.chat("确认办理", session_id=session_id)
        print(f"步骤3: {r3['response']}")
        print(f"数据: {r3.get('data', {}).get('success')}")  # True ✅

    #场景2：转移到无关话题（应清除）
    def test_unrelated(self,chatbot):
        session_id = "test_unrelated"

        # 第1步：发起办理
        r1 = chatbot.chat("办理畅游套餐，13800138000", session_id=session_id)
        print(f"待确认: {r1['state']['pending_confirmation']}")  # True

        # 第2步：查询余额（无关话题）
        r2 = chatbot.chat("查一下我的余额", session_id=session_id)
        print(f"待确认: {r2['state']['pending_confirmation']}")  # False ✅ 已清除

        # 第3步：再说确认（不会执行之前的办理）
        r3 = chatbot.chat("确认", session_id=session_id)
        print(f"响应: {r3['response']}")  # 不会执行办理 ✅

    # 场景3：超时测试
    def test_timeout(self, chatbot):
        session_id = "test_timeout"

        # 第1步：发起办理
        chatbot.chat("办理无限套餐，13800138000", session_id=session_id)

        # 第2步：等待超过5分钟（实际测试可以修改超时时间为10秒）
        time.sleep(301)  # 5分1秒

        # 第3步：确认
        r3 = chatbot.chat("确认", session_id=session_id)
        print(f"响应: {r3['response']}")
        # 预期："抱歉，确认已超时..." ✅

    # 场景4：友好提醒（可选功能）
    def test_reminder(self, chatbot):
        session_id = "test_reminder"

        # 第1步：发起办理
        chatbot.chat("办理经济套餐，13800138000", session_id=session_id)

        # 第2步：查询当前套餐（跨领域，但可以提醒）
        r2 = chatbot.chat("我现在用的什么套餐", session_id=session_id)
        print(f"响应: {r2['response']}")
        # 预期包含："💡 提示：您还有一个待确认的套餐办理..." ✅


