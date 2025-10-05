"""
Redis连接管理器
"""
import redis
from redis.connection import ConnectionPool
from typing import Optional
from config import settings
from utils.logger import logger


class RedisManager:
    """Redis连接管理器 - 单例模式"""

    _instance = None
    _pool: Optional[ConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化Redis连接池"""
        try:
            connection_params = {
                'host': settings.REDIS_HOST,
                'port': settings.REDIS_PORT,
                'db': settings.REDIS_DB,
                'max_connections': settings.get('REDIS_MAX_CONNECTIONS', 50),
                'decode_responses': True,
                'socket_timeout': 5,
                'socket_connect_timeout': 5,
                'retry_on_timeout': True
            }

            # 如果有密码
            if hasattr(settings, 'REDIS_PASSWORD') and settings.REDIS_PASSWORD:
                connection_params['password'] = settings.REDIS_PASSWORD

            self._pool = ConnectionPool(**connection_params)

            logger.info(f"Redis连接池初始化成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
        except Exception as e:
            logger.error(f"Redis连接池初始化失败: {e}")
            self._pool = None

    def get_client(self) -> redis.Redis:
        """获取Redis客户端"""
        if self._pool is None:
            raise RuntimeError("Redis连接池未初始化")
        return redis.Redis(connection_pool=self._pool)

    def test_connection(self) -> bool:
        """测试连接"""
        try:
            client = self.get_client()
            client.ping()
            logger.info("Redis连接测试成功")
            return True
        except Exception as e:
            logger.error(f"Redis连接测试失败: {e}")
            return False

    def get_info(self) -> dict:
        """获取Redis信息"""
        try:
            client = self.get_client()
            return client.info()
        except Exception as e:
            logger.error(f"获取Redis信息失败: {e}")
            return {}

    def close(self):
        """关闭连接池"""
        if self._pool:
            self._pool.disconnect()
            logger.info("Redis连接池已关闭")


