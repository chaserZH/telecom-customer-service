"""
质量评估器测试
"""
import pytest
from core.dst.dialog_state import DialogState, DialogTurn
from core.evaluation import DialogQualityEvaluator


class TestDialogQualityEvaluator:
    """质量评估器测试"""

    @pytest.fixture
    def evaluator(self):
        """创建评估器实例"""
        return DialogQualityEvaluator()

    def test_evaluate_completed_task(self, evaluator):
        """测试已完成任务评估"""
        state = DialogState(
            session_id="test_001",
            current_intent="query_packages",
            turn_count=3,
            is_completed=True
        )

        metrics = evaluator.evaluate(state)

        assert metrics["task_success"] == 1.0
        assert "efficiency" in metrics
        assert "overall_score" in metrics

    def test_evaluate_efficiency(self, evaluator):
        """测试效率评估"""
        # 最优轮次
        state1 = DialogState(
            session_id="test_002",
            current_intent="query_packages",
            turn_count=2
        )

        metrics1 = evaluator.evaluate(state1)
        assert metrics1["efficiency"] == 1.0

        # 超过最优轮次
        state2 = DialogState(
            session_id="test_003",
            current_intent="query_packages",
            turn_count=5
        )

        metrics2 = evaluator.evaluate(state2)
        assert metrics2["efficiency"] < 1.0