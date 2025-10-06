"""
推荐引擎测试
"""
import pytest
from core.recommendation import RecommendationEngine
from core.dst.dialog_state import DialogState


class TestRecommendationEngine:
    """推荐引擎测试"""

    @pytest.fixture
    def recommender(self):
        """创建推荐引擎实例"""
        return RecommendationEngine()

    def test_no_recommendation_for_single_result(self, recommender):
        """测试单个结果不推荐"""
        state = DialogState(session_id="test_001")
        query_result = {
            "success": True,
            "count": 1,
            "data": [{"name": "经济套餐", "price": 50}]
        }

        recommendation = recommender.recommend(state, query_result)

        assert recommendation is None

    def test_recommendation_for_multiple_results(self, recommender):
        """测试多结果推荐"""
        state = DialogState(
            session_id="test_002",
            slots={"price_max": 100, "data_min": 50}
        )
        query_result = {
            "success": True,
            "count": 3,
            "data": [
                {"name": "经济套餐", "price": 50, "data_gb": 10, "target_user": "无限制"},
                {"name": "畅游套餐", "price": 180, "data_gb": 100, "target_user": "无限制"},
                {"name": "校园套餐", "price": 150, "data_gb": 200, "target_user": "在校生"}
            ]
        }

        recommendation = recommender.recommend(state, query_result)

        assert recommendation is not None
        assert "package" in recommendation
        assert "reason" in recommendation