# 用户数据模型
from dataclasses import dataclass
from typing import Optional


@dataclass
class User:
    """用户模型"""
    phone: str
    current_package_id: Optional[int] = None
    monthly_usage_gb: float = 0.0
    balance: float = 0.0
    status: int = 1

    def to_dict(self):
        """转为字典"""
        return {
            "phone": self.phone,
            "current_package_id": self.current_package_id,
            "monthly_usage_gb": self.monthly_usage_gb,
            "balance": self.balance,
            "status": self.status
        }
