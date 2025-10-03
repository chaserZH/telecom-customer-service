"""
Function Calling 定义
"""
from enum import Enum
from typing import Dict, List


class FunctionCategory(Enum):
    """Function分类"""
    PACKAGE_QUERY = "query_packages"
    USER_INFO = "user_info"
    BUSINESS_CONSULT = "business_consult"
    ORDER_OPERATION = "order_operation"


# Function定义列表
FUNCTION_DEFINITIONS =[
    {
        "type":"function",
        "function":{
            "name":"query_packages",
            "description": "查询符合条件的流量套餐列表。当用户想了解套餐、比较套餐、查找合适的套餐时使用",
            "parameters": {
                "type":"object",
                "properties": {
                    "price_min":{
                        "type":"number",
                        "description": "最低价格(元/月),例如'50元以上'表示price_min=50"
                    },
                    "price_max":{
                        "type":"number",
                        "description": "最高价格(元/月),例如'100元以内'、'不超过200'表示price_max=100或200"
                    },
                    "data_max":{
                        "type":"number",
                        "description": "最多流量(GB/月)"
                    },
                    "target_user": {
                        "type": "string",
                        "enum": ["无限制", "在校生"],
                        "description": "适用人群。'学生套餐'、'校园套餐'对应'在校生'"
                    },
                    "sort_by": {
                        "type": "string",
                        "enum": ["price_asc", "price_desc", "data_desc"],
                        "description": "排序方式。price_asc=价格升序(便宜优先), price_desc=价格降序, data_desc=流量降序",
                        "default": "price_asc"
                    }
                }
            },
            "required": []
        }
    },
    {
        "type":"function",
        "function": {
            "name": "query_current_package",
            "description": "查询用户当前使用的套餐信息。当用户询问'我现在是什么套餐'、'我的套餐'、'当前套餐'时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "手机号码,11位数字,格式如13800138000"
                    }
                },
                "required": ["phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_package_detail",
            "description": "查询指定套餐的详细信息。当用户询问某个具体套餐的详情时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "package_name": {
                        "type": "string",
                        "enum": ["经济套餐", "畅游套餐", "无限套餐", "校园套餐"],
                        "description": "套餐名称"
                    }
                },
                "required": ["package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "change_package",
            "description": "办理套餐变更。当用户明确要求更换/办理某个套餐时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "手机号码"
                    },
                    "new_package_name": {
                        "type": "string",
                        "enum": ["经济套餐", "畅游套餐", "无限套餐", "校园套餐"],
                        "description": "要更换的新套餐名称"
                    }
                },
                "required": ["phone", "new_package_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_usage",
            "description": "查询用户的流量、话费使用情况。当用户询问'用了多少流量'、'话费余额'、'剩余流量'时使用",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {
                        "type": "string",
                        "description": "手机号码"
                    },
                    "query_type": {
                        "type": "string",
                        "enum": ["data", "balance", "all"],
                        "description": "查询类型: data=流量使用, balance=余额, all=全部",
                        "default": "all"
                    }
                },
                "required": ["phone"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "business_consultation",
            "description": "业务咨询和政策说明。当用户询问业务规则、办理流程、优惠活动等非数据查询问题时使用(预留RAG接口)",
            "parameters": {
                "type": "object",
                "properties": {
                    "question": {
                        "type": "string",
                        "description": "用户的咨询问题"
                    },
                    "business_type": {
                        "type": "string",
                        "enum": ["套餐说明", "办理流程", "资费规则", "优惠活动", "其他"],
                        "description": "业务类型分类"
                    }
                },
                "required": ["question"]
            }
        }
    }
]

def get_function_by_name(function_name: str) -> Dict:
    """根据名称获取Function定义"""
    for func_def in FUNCTION_DEFINITIONS:
        if func_def["function"]["name"] == function_name:
            return func_def["function"]
    return None

def get_required_params(function_name: str) -> List[str]:
    """获取必填参数列表"""
    func = get_function_by_name(function_name)
    if func:
        return func["parameters"].get("required", [])
    return []


