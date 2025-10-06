"""
NLG模块测试
"""
import pytest
from core.policy import Action, ActionType
from core.dst.dialog_state import DialogState
from core.nlg import NLGGenerator


class TestNLGGenerator:
    """NLG生成器测试"""

    @pytest.fixture
    def nlg(self):
        """创建NLG实例"""
        return NLGGenerator()

    def test_template_generation(self, nlg):
        """测试模板生成"""
        action = Action(
            action_type=ActionType.REQUEST,
            intent="query_packages",
            parameters={"slot": "phone"}
        )
        state = DialogState(session_id="test_001")

        response = nlg.generate(action, state)

        assert "手机号" in response
        assert len(response) < 100

    def test_inform_generation(self, nlg):
        """测试告知生成"""
        action = Action(
            action_type=ActionType.INFORM,
            intent="query_packages",
            parameters={
                "success": True,
                "count": 1,
                "data": [{
                    "name": "经济套餐",
                    "price": 50,
                    "data_gb": 10,
                    "voice_minutes": 100,
                    "target_user": "无限制",
                    "description": "适合轻度用户"
                }]
            }
        )
        state = DialogState(session_id="test_002")

        response = nlg.generate(action, state)

        assert "经济套餐" in response
        assert "50" in response

    def test_confirm_generation(self, nlg):
        """测试确认生成"""
        action = Action(
            action_type=ActionType.CONFIRM,
            intent="change_package",
            parameters={
                "phone": "13800138000",
                "new_package_name": "畅游套餐",
                "price": 180
            }
        )
        state = DialogState(session_id="test_003")

        response = nlg.generate(action, state)

        assert "13800138000" in response
        assert "畅游套餐" in response
        assert "确认" in response
