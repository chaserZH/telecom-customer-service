# 套餐数据模型
from dataclasses import dataclass
from typing import Optional


@dataclass
class Pacakge:
    """套餐模型"""
    id : int
    name : str
    data_gb: int
    price: float
    target_user: str
    description: Optional[str] = None
    status: int = 1

    def to_dict(self):
        """转为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "data_gb": self.data_gb,
            "price": self.price,
            "target_user": self.target_user,
            "description": self.description
        }
