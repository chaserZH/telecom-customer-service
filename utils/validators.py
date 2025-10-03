# 数据验证器
import re


def validate_phone(phone: str) -> bool:
    """验证手机号格式"""
    if not phone:
        return False
    pattern = r'^1[3-9]\d{9}$'
    return bool(re.match(pattern, phone))

def validate_price(price: float) -> bool:
    """验证价格"""
    return price > 0

def validate_data_gb(data_gb: int) -> bool:
    """验证流量"""
    return data_gb > 0