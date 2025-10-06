"""
核心业务逻辑模块
包含NLU引擎、DST、Policy、NLG等核心功能
"""

# 第一阶段：NLU
from .nlu import (
    NLUEngine,
    NLUResult,
    FUNCTION_DEFINITIONS,
    get_function_by_name,
    FunctionCategory,
    get_required_params
)

# 第二阶段：DST
from .dst import (
    DialogState,
    DialogTurn,
    DialogStateTracker,
    SlotManager,
    ContextManager
)

# 第三阶段：Policy + NLG ⭐
from .policy import (
    Action,
    ActionType,
    PolicyEngine,
    ConfirmationManager
)

from .nlg import (
    NLGGenerator,
    RESPONSE_TEMPLATES
)

from .recommendation import RecommendationEngine
from .evaluation import DialogQualityEvaluator

# 对话系统
from .chatbot_nlu import TelecomChatbotNlu
from .chatbot_dst import TelecomChatbotDst
from .chatbot_policy import TelecomChatbotPolicy

__all__ = [
    # NLU模块
    'NLUEngine',
    'NLUResult',
    'FUNCTION_DEFINITIONS',
    'get_function_by_name',
    'FunctionCategory',
    'get_required_params',

    # DST模块
    'DialogState',
    'DialogTurn',
    'DialogStateTracker',
    'SlotManager',
    'ContextManager',

    # Policy模块
    'Action',
    'ActionType',
    'PolicyEngine',
    'ConfirmationManager',

    # NLG模块
    'NLGGenerator',
    'RESPONSE_TEMPLATES',

    # 高级特性
    'RecommendationEngine',
    'DialogQualityEvaluator',

    # 对话系统
    'TelecomChatbotNlu',
    'TelecomChatbotDst',
    'TelecomChatbotPolicy'
]

