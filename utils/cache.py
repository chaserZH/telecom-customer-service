"""
缓存工具
"""
import time
import hashlib
from typing import Optional, Any
from utils.logger import logger


class ResponseCache:
    """响应缓存"""

    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """
        初始化缓存

        Args:
            ttl: 缓存存活时间（秒）
            max_size: 最大缓存数量
        """
        self.cache = {}
        self.ttl = ttl
        self.max_size = max_size
        logger.info(f"响应缓存初始化: TTL={ttl}s, MaxSize={max_size}")

    def get(self, cache_key: str) -> Optional[str]:
        """
        获取缓存

        Args:
            cache_key: 缓存键

        Returns:
            Optional[str]: 缓存的响应
        """
        if cache_key not in self.cache:
            return None

        cached = self.cache[cache_key]

        # 检查是否过期
        if time.time() - cached["time"] > self.ttl:
            del self.cache[cache_key]
            logger.debug(f"缓存过期: {cache_key[:20]}...")
            return None

        logger.debug(f"缓存命中: {cache_key[:20]}...")
        return cached["response"]

    def set(self, cache_key: str, response: str):
        """
        设置缓存

        Args:
            cache_key: 缓存键
            response: 响应内容
        """
        # 检查容量
        if len(self.cache) >= self.max_size:
            self._evict_oldest()

        self.cache[cache_key] = {
            "response": response,
            "time": time.time()
        }

        logger.debug(f"缓存设置: {cache_key[:20]}...")

    def _evict_oldest(self):
        """移除最老的缓存"""
        if not self.cache:
            return

        oldest_key = min(self.cache.keys(), key=lambda k: self.cache[k]["time"])
        del self.cache[oldest_key]
        logger.debug(f"缓存淘汰: {oldest_key[:20]}...")

    @staticmethod
    def generate_key(action_type: str, intent: str, parameters: Any) -> str | None:
        """
        生成缓存键

        Args:
            action_type: 动作类型
            intent: 意图
            parameters: 参数

        Returns:
            str: 缓存键
        """
        # 只对确定性响应生成缓存键
        if action_type not in ["REQUEST", "CONFIRM"]:
            return None

        # 生成哈希键
        key_str = f"{action_type}_{intent}_{str(parameters)}"
        return hashlib.md5(key_str.encode()).hexdigest()

    def clear(self):
        """清空缓存"""
        self.cache.clear()
        logger.info("缓存已清空")

    def stats(self) -> dict:
        """
        获取缓存统计

        Returns:
            dict: 统计信息
        """
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "ttl": self.ttl
        }