# nlu模块
# core/nlu/__init__.py
"""
NLU（自然语言理解）模块
包含意图识别、槽位填充等NLU功能
"""


from .nlu_engine import NLUEngine,NLUResult
from .function_definitions import (
    FUNCTION_DEFINITIONS,
    get_function_by_name,
    get_required_params,
    FunctionCategory
)


# 定义通过 from core.nlu import * 可以导入的内容
__all__ = [
    'NLUEngine',  # NLU引擎主类 - nlu包的核心导出，
    'NLUResult' ,
    'FUNCTION_DEFINITIONS',
    'get_function_by_name',
    'FunctionCategory',
    'get_required_params',
]

