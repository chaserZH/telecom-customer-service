"""
Policy模块测试
"""
import pytest
from core.dst.dialog_state import DialogState
from core.policy import PolicyEngine, Action, ActionType


class TestPolicyEngine:
    """Policy引擎测试"""

    @pytest.fixture
    def policy(self):
        """创建Policy实例"""
        return PolicyEngine()

    def test_error_handling(self, policy):
        """测试错误处理"""
        state = DialogState(
            session_id="test_001",
            current_intent="query_packages"
        )
        exec_result = {
            "success": False,
            "error": "数据库连接失败"
        }

        action = policy.decide(state, exec_result)

        assert action.action_type == ActionType.APOLOGIZE
        assert "error" in action.parameters
        assert action.intent == "query_packages"

    def test_slot_request(self, policy):
        """测试槽位请求"""
        state = DialogState(
            session_id="test_002",
            current_intent="query_current_package",
            needs_clarification=True,
            missing_slots=["phone"]
        )

        action = policy.decide(state)

        assert action.action_type == ActionType.REQUEST
        assert action.parameters["slot"] == "phone"

    def test_confirmation_required(self, policy):
        """测试确认流程"""
        state = DialogState(
            session_id="test_003",
            current_intent="change_package",
            slots={
                "phone": "13800138000",
                "new_package_name": "畅游套餐",
                "price": 180
            }
        )

        action = policy.decide(state)

        assert action.action_type == ActionType.CONFIRM
        assert action.requires_confirmation

    def test_success_inform(self, policy):
        """测试成功告知"""
        state = DialogState(
            session_id="test_004",
            current_intent="query_packages",
            slots={"price_max": 100}
        )
        exec_result = {
            "success": True,
            "count": 2,
            "data": [
                {"name": "经济套餐", "price": 50},
                {"name": "畅游套餐", "price": 180}
            ]
        }

        action = policy.decide(state, exec_result)

        assert action.action_type == ActionType.INFORM
        assert "data" in action.parameters