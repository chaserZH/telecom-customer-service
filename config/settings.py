# 系统配置文件
# -*- coding: utf-8 -*-
"""
系统配置文件
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """系统配置"""

    # 应用配置
    APP_NAME: str = "电信套餐AI客服系统"
    VERSION: str = "0.2.0"
    DEBUG: bool = True

    # 大模型配置
    LLM_PROVIDER: str = "deepseek"  # openai / anthropic / deepseek

    # DeepSeek配置
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # OpenAI配置（备用）
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4"

    # # Anthropic配置（备用）
    # ANTHROPIC_API_KEY: Optional[str] = None
    # ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # 数据库配置
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = "password"
    DB_NAME: str = "telecom_chatbot"

    # Redis配置
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None
    REDIS_MAX_CONNECTIONS: int = 50

    # # RAG配置 (预留)
    # RAG_ENABLED: bool = False
    # VECTOR_DB_TYPE: str = "milvus"

    # 会话配置
    SESSION_TIMEOUT: int = 1800  # 30分钟
    MAX_CONTEXT_TURNS: int = 10

    # 确认相关配置
    # 🔥 新增：确认相关配置（带类型注解）
    CONFIRMATION_TIMEOUT_MINUTES: int = 5  # 确认超时时间（分钟）
    CONFIRMATION_STRICT_MODE: bool = False  # 严格模式
    CONFIRMATION_REMINDER: bool = True  # 是否启用友好提醒

    # API配置
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    @property
    def database_url(self) -> str:
        """数据库连接URL"""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    @property
    def redis_url(self) -> str:
        """Redis连接URL"""
        if self.REDIS_PASSWORD:
            return f"redis://:{self.REDIS_PASSWORD}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    class Config:
        env_file = ".env"
        case_sensitive = True
        # 允许额外的字段（兼容TOMMY_DEEPSEEK_API_KEY这样的命名）
        extra = "ignore"
        env_file_encoding = "utf-8"

