"""
NLG模块
自然语言生成
"""

from .nlg_generator import NLGGenerator
from .templates import RESPONSE_TEMPLATES

__all__ = [
    'NLGGenerator',
    'RESPONSE_TEMPLATES'
]
