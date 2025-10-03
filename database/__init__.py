# 数据库
from .db_manager import DatabaseManager
from .redis_manager import RedisManager

# 全局数据库管理器实例
db_manager = DatabaseManager()

# 全局实例
redis_manager = RedisManager()

__all__ = ['db_manager', 'redis_manager']