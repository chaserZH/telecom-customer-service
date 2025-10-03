# 配置模块
# -*- coding: utf-8 -*-

# config/__init__.py
from .settings import Settings
from .prompts import SLOT_QUESTIONS, SYSTEM_PROMPT

# 创建全局配置实例 - 整个项目共享同一个配置
settings = Settings()

# 定义通过 from config import * 可以导入的内容
__all__ = [
    'Settings',          # 配置类
    'settings',          # 配置实例
    'SLOT_QUESTIONS',  # Prompt模板
    'SYSTEM_PROMPT'     # 系统Prompt
]