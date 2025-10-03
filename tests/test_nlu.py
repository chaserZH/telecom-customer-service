"""
NLU模块单元测试
"""
import pytest
from core.nlu.nlu_engine import NLUEngine
from utils import logger


class TestNLUEngine:
    """NLU引擎测试"""

    @pytest.fixture
    def nlu_engine(self):
        """创建NLU引擎实例"""
        return NLUEngine()

    def test_price_query(self, nlu_engine):
        """测试价格查询"""
        result = nlu_engine.understand(
            "有100块以内的套餐吗",
            session_id="test_001"
        )

        logger.info(f"返回结果: {result}")

        assert result.intent == "query_packages"
        assert result.parameters.get("price_max") == 100
        assert result.parameters.get("data_min") == 50