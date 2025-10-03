
"""
数据库管理器
"""
from sqlalchemy import create_engine, QueuePool, text
from sqlalchemy.orm import sessionmaker, Session

from config import settings
from utils import logger


class DatabaseManager:
    """数据库管理器"""

    _instance = None
    _engine = None
    _session_factory = None

    def __new__(cls):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """初始化数据库连接"""
        try:
            self._engine = create_engine(
                settings.database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_recycle=3600,
                echo=settings.DEBUG
            )
            self._session_factory = sessionmaker(bind=self._engine)
            logger.info("数据库连接初始化成功")
        except Exception as e:
            logger.error(f"数据库连接初始化失败: {e}")
            raise

    def get_session(self) -> Session:
        """获取数据库会话"""
        return self._session_factory()

    def execute_query(self, query: str, params: dict = None) -> list:
        """执行查询"""
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            return result.fetchall()

    def execute_update(self, query: str, params: dict = None) -> int:
        """执行更新"""
        with self.get_session() as session:
            result = session.execute(text(query), params or {})
            session.commit()
            return result.rowcount