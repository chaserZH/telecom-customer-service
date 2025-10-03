"""
数据库执行器单元测试
"""
import pytest
from executor.db_executor import DatabaseExecutor


class TestDatabaseExecutor:
    """数据库执行器测试"""

    @pytest.fixture
    def db_executor(self):
        """创建数据库执行器实例"""
        return DatabaseExecutor()

    def test_query_packages(self, db_executor):
        """测试套餐查询"""
        result = db_executor.query_packages(price_max=100)

        assert result["success"]
        assert "data" in result
        assert all(pkg["price"] <= 100 for pkg in result["data"])

    def test_query_current_package(self, db_executor):
        """测试当前套餐查询"""
        result = db_executor.query_current_package(phone="13800138000")

        assert result["success"]
        assert result["data"]["phone"] == "13800138000"
        assert "package_name" in result["data"]

    def test_invalid_phone(self, db_executor):
        """测试无效手机号"""
        result = db_executor.query_current_package(phone="123")

        assert not result["success"]
        assert "error" in result