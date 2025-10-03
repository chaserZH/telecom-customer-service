# -*- coding: utf-8 -*-
"""
DST模块单元测试
"""
import pytest
from datetime import datetime

from core.dst.dialog_state import DialogState, DialogTurn
from core.dst.dialog_state_tracker import DialogStateTracker
from core.dst.slot_manager import SlotManager
from core.dst.context_manager import ContextManager
from core.nlu.nlu_engine import NLUResult


class TestDialogState:
    """对话状态测试"""

    def test_create_state(self):
        """测试创建状态"""
        state = DialogState(session_id="test_001")
        assert state.session_id == "test_001"
        assert state.turn_count == 0
        assert len(state.slots) == 0

    def test_add_turn(self):
        """测试添加对话轮次"""
        state = DialogState(session_id="test_002")
        state.add_turn("user", "你好", "greeting")

        assert state.turn_count == 1
        assert len(state.history) == 1
        assert state.history[0].role == "user"
        assert state.history[0].content == "你好"

    def test_state_serialization(self):
        """测试状态序列化"""
        state = DialogState(session_id="test_003")
        state.slots = {"phone": "13800138000"}
        state.add_turn("user", "测试")

        # 转为字典
        state_dict = state.to_dict()
        assert state_dict["session_id"] == "test_003"
        assert state_dict["slots"]["phone"] == "13800138000"

        # 从字典恢复
        restored_state = DialogState.from_dict(state_dict)
        assert restored_state.session_id == "test_003"
        assert restored_state.slots["phone"] == "13800138000"


class TestSlotManager:
    """槽位管理器测试"""

    @pytest.fixture
    def slot_manager(self):
        return SlotManager()

    def test_fill_slots_same_intent(self, slot_manager):
        """测试相同意图下的槽位填充"""
        current_slots = {"price_max": 100}
        new_slots = {"data_min": 50}

        result = slot_manager.fill_slots(
            current_slots, new_slots,
            "query_packages", "query_packages"
        )

        assert result["price_max"] == 100  # 保留
        assert result["data_min"] == 50  # 新增

    def test_fill_slots_intent_changed(self, slot_manager):
        """测试意图改变时的槽位填充"""
        current_slots = {"price_max": 100, "phone": "13800138000"}
        new_slots = {}

        result = slot_manager.fill_slots(
            current_slots, new_slots,
            "query_packages", "query_current_package"
        )

        assert result.get("phone") == "13800138000"  # 用户信息保留
        assert "price_max" not in result  # 业务槽位清除

    def test_validate_slots(self, slot_manager):
        """测试槽位验证"""
        slots = {"price_max": 100}
        required = ["phone", "package_name"]

        missing = slot_manager.validate_slots(slots, required)

        assert "phone" in missing
        assert "package_name" in missing
        assert len(missing) == 2


class TestContextManager:
    """上下文管理器测试"""

    @pytest.fixture
    def context_manager(self):
        return ContextManager()

    def test_update_context(self, context_manager):
        """测试更新上下文"""
        context_stack = []
        nlu_result = NLUResult(
            intent="query_packages",
            parameters={"price_max": 100},
            confidence=0.9
        )

        new_stack = context_manager.update_context(context_stack, nlu_result)

        assert len(new_stack) == 1
        assert new_stack[0]["intent"] == "query_packages"

    def test_clean_expired_context(self, context_manager):
        """测试清理过期上下文"""
        from datetime import timedelta

        old_time = datetime.now() - timedelta(seconds=400)
        context_stack = [
            {"intent": "old", "timestamp": old_time},
            {"intent": "new", "timestamp": datetime.now()}
        ]

        cleaned = context_manager._clean_expired_context(context_stack)

        assert len(cleaned) == 1
        assert cleaned[0]["intent"] == "new"


class TestDialogStateTracker:
    """对话状态跟踪器测试"""

    @pytest.fixture
    def dst(self):
        return DialogStateTracker()

    def test_track_new_session(self, dst):
        """测试跟踪新会话"""
        nlu_result = NLUResult(
            intent="query_packages",
            parameters={"price_max": 100},
            confidence=0.9
        )
        nlu_result.raw_input = "有100元以内的套餐吗"

        state = dst.track("test_session", nlu_result)

        assert state.session_id == "test_session"
        assert state.current_intent == "query_packages"
        assert state.slots["price_max"] == 100
        assert state.turn_count > 0

    def test_track_multi_turn(self, dst):
        """测试多轮对话跟踪"""
        session_id = "multi_turn_test"

        # 第一轮
        nlu_result1 = NLUResult(
            intent="query_packages",
            parameters={"price_max": 100},
            confidence=0.9
        )
        nlu_result1.raw_input = "100元以内"
        state1 = dst.track(session_id, nlu_result1)

        # 第二轮
        nlu_result2 = NLUResult(
            intent="query_packages",
            parameters={"data_min": 50},
            confidence=0.9
        )
        nlu_result2.raw_input = "流量50G以上"
        state2 = dst.track(session_id, nlu_result2)

        # 验证槽位继承
        assert state2.slots["price_max"] == 100  # 继承
        assert state2.slots["data_min"] == 50  # 新增
        assert state2.turn_count == 2