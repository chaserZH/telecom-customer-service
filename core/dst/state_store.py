"""
状态存储 - Redis实现
"""
import json

from config import settings
from core.dst.dialog_state import DialogState
from database import redis_manager
from utils import logger


class StateStore:
    """状态存储 - Redis实现"""

    def __init__(self):
        """初始化"""
        try:
            self.redis = redis_manager.get_client()
            self.use_redis = redis_manager.test_connection()

            if not self.use_redis:
                logger.warning("Redis不可用，降级到内存存储")
                self.memory_store = {}
        except Exception as e:
            logger.error(f"Redis初始化失败: {e}, 使用内存存储")
            self.use_redis = False
            self.memory_store = {}

        self.ttl = settings.SESSION_TIMEOUT  # 默认30分钟

    def save(self, session_id: str, state: DialogState):
        """
        保存状态

        Args:
            session_id: 会话ID
            state: 对话状态
        """
        if self.use_redis:
            try:
                self._save_to_redis(session_id, state)
            except Exception as e:
                logger.error(f"保存到Redis失败: {e}, 降级到内存")
                self.use_redis = False
                self._save_to_memory(session_id, state)
        else:
            self._save_to_memory(session_id, state)

    def _save_to_redis(self, session_id: str, state: DialogState):
        """保存到Redis"""
        key = f"session:{session_id}:state"

        # 序列化状态
        state_dict = state.to_dict()
        state_json = json.dumps(state_dict, ensure_ascii=False, default=str)

        # 使用Pipeline提高性能
        pipe = self.redis.pipeline()
        pipe.set(key, state_json)
        pipe.expire(key, self.ttl)

        # 同时保存到用户会话列表
        if state.user_phone:
            user_key = f"user:{state.user_phone}:sessions"
            pipe.sadd(user_key, session_id)
            pipe.expire(user_key, 604800)  # 7天

        pipe.execute()

        logger.debug(f"状态已保存到Redis: {session_id}")

    def _save_to_memory(self, session_id: str, state: DialogState):
        """保存到内存"""
        self.memory_store[session_id] = state
        logger.debug(f"状态已保存到内存: {session_id}")

    def load(self, session_id: str) -> DialogState:
        """
        加载状态

        Args:
            session_id: 会话ID

        Returns:
            对话状态，如果不存在则返回新状态
        """
        if self.use_redis:
            try:
                return self._load_from_redis(session_id)
            except Exception as e:
                logger.error(f"从Redis加载失败: {e}")
                return self._load_from_memory(session_id)
        else:
            return self._load_from_memory(session_id)

    def _load_from_redis(self, session_id: str) -> DialogState:
        """从Redis加载"""
        key = f"session:{session_id}:state"
        data = self.redis.get(key)

        if not data:
            logger.debug(f"Redis中不存在会话: {session_id}, 返回新状态")
            return DialogState(session_id=session_id)

        # 反序列化
        state_dict = json.loads(data)
        state = DialogState.from_dict(state_dict)

        logger.debug(f"从Redis加载状态: {session_id}")
        return state

    def _load_from_memory(self, session_id: str) -> DialogState:
        """从内存加载"""
        if session_id in self.memory_store:
            logger.debug(f"从内存加载状态: {session_id}")
            return self.memory_store[session_id]

        logger.debug(f"内存中不存在会话: {session_id}, 返回新状态")
        return DialogState(session_id=session_id)

    def delete(self, session_id: str):
        """
        删除状态

        Args:
            session_id: 会话ID
        """
        if self.use_redis:
            try:
                key = f"session:{session_id}:state"
                self.redis.delete(key)
                logger.info(f"从Redis删除会话: {session_id}")
            except Exception as e:
                logger.error(f"从Redis删除失败: {e}")

        if session_id in self.memory_store:
            del self.memory_store[session_id]
            logger.info(f"从内存删除会话: {session_id}")

    def exists(self, session_id: str) -> bool:
        """检查状态是否存在"""
        if self.use_redis:
            try:
                key = f"session:{session_id}:state"
                return self.redis.exists(key) > 0
            except:
                pass

        return session_id in self.memory_store

    def get_user_sessions(self, user_phone: str) -> list:
        """获取用户的所有会话"""
        if not self.use_redis:
            return []

        try:
            user_key = f"user:{user_phone}:sessions"
            sessions = self.redis.smembers(user_key)
            return list(sessions)
        except Exception as e:
            logger.error(f"获取用户会话列表失败: {e}")
            return []