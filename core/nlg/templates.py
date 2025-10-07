"""
响应模板库
"""
from typing import Dict, List, Union

# 响应模板库
RESPONSE_TEMPLATES: Dict[str, Dict[str, Union[str, List[str], Dict]]] = {
    # REQUEST类模板
    "REQUEST": {
        "phone": [
            "请问您的手机号是多少呢？",
            "为了查询您的信息，需要您提供手机号码",
            "可以告诉我您的手机号码吗？"
        ],
        "package_name": [
            "请问您想了解哪个套餐？我们有经济套餐、畅游套餐、无限套餐和校园套餐",
            "您想办理哪个套餐呢？"
        ],
        "new_package_name": [
            "请问您想更换为哪个套餐？",
            "您想办理哪个新套餐呢？"
        ],
        "query_type": [
            "您想查询流量使用情况还是话费余额？",
            "需要查询流量还是余额呢？"
        ],
        "default": "请提供{slot}信息"
    },

    # INFORM类模板
    "INFORM": {
        "query_packages": {
            "single": """找到了【{name}】套餐:
💰 月费: {price}元
📊 流量: {data_gb}GB/月
📞 通话: {voice_minutes}分钟/月
👥 适用: {target_user}

{description}""",

            "multiple": "为您找到 {count} 个合适的套餐:\n\n{package_list}",

            "empty": "抱歉，没有找到完全符合条件的套餐。要不要看看其他套餐？或者可以调整一下筛选条件",

            "with_recommendation": "为您找到 {count} 个套餐。{recommendation}"
        },

        "query_current_package": """📱 您当前使用的是【{package_name}】

套餐内容:
  • 流量: {data_gb}GB/月
  • 通话: {voice_minutes}分钟/月
  • 月费: {price}元

使用情况:
  • 本月已用流量: {monthly_usage_gb}GB
  • 本月已用通话: {monthly_usage_minutes}分钟
  • 账户余额: {balance}元""",

        "query_package_detail": """【{name}】套餐详情

💰 月费: {price}元
📊 每月流量: {data_gb}GB
📞 每月通话: {voice_minutes}分钟
👥 适用人群: {target_user}

📝 套餐说明:
{description}

如需办理，请告诉我您的手机号码""",

        # 修改 change_package 模板（提供简化版和详细版）
        "change_package": [
            "已成功为您办理【{new_package_name}】，次月生效！",  # 简化版（推荐）
            "办理成功！您的【{new_package_name}】将在下月生效"
        ],

        "query_usage": """📱 {phone} 的使用情况:

📈 本月已用流量: {monthly_usage_gb}GB
📞 本月已用通话: {monthly_usage_minutes}分钟
💳 账户余额: {balance}元""",

        "default": "处理完成"
    },

    # CONFIRM类模板
    "CONFIRM": {
        # 修改 change_package 确认模板
        "change_package": [
            "请确认：为手机号 {phone} 办理【{new_package_name}】套餐，是否确认？",
            "确认为 {phone} 更换为【{new_package_name}】吗？"
        ],
        "cancel_service": [
            "确认为 {phone} 取消服务吗？此操作不可恢复",
            "请确认是否取消 {phone} 的服务"
        ],
        "default": "请确认您的操作: {intent}"
    },

    # APOLOGIZE类模板
    "APOLOGIZE": {
        "system_error": [
            "抱歉，系统遇到了一些问题，请稍后再试",
            "系统繁忙，请稍后重试"
        ],
        "not_found": [
            "抱歉，{error}",
            "未找到相关信息: {error}"
        ],
        "invalid_input": [
            "您提供的{error}，请重新输入",
            "输入有误: {error}"
        ],
        "unknown_error": [
            "抱歉，处理出现问题",
            "遇到了一些问题，请重试"
        ],
        "default": "抱歉，{error}"
    },

    # RECOMMEND类模板
    "RECOMMEND": {
        "price_sensitive": "根据您的预算，推荐【经济套餐】，性价比最高",
        "heavy_user": "根据您的使用情况，建议选择【畅游套餐】或【无限套餐】",
        "student": "作为学生用户，推荐【校园套餐】，专享优惠",
        "default": "根据您的需求，推荐{package_name}"
    },

    # CLARIFY类模板
    "CLARIFY": {
        "ambiguous_intent": [
            "您是想查询套餐还是办理套餐呢？",
            "不太明白您的意思，能否说得更详细一些？"
        ],
        "multiple_matches": "有多个匹配项，请明确您的选择",
        "default": "请问您的具体需求是什么？"
    },

    # CLOSE类模板
    "CLOSE": {
        "satisfied": [
            "还有什么可以帮您的吗？",
            "如有其他问题，随时咨询我",
            "感谢使用，祝您生活愉快！"
        ],
        "unsatisfied": "如果还有疑问，欢迎继续咨询",
        "default": "还需要其他帮助吗？"
    }
}