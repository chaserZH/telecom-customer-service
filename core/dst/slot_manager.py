"""
槽位管理器
"""
from typing import Dict, Any, List, Set
from utils import logger


class SlotManager:
    """槽位管理器"""

    # 用户信息槽位（跨意图继承）
    USER_INFO_SLOTS: Set[str] = {'phone', 'name', 'user_id', 'user_name'}

    # 相同领域的意图（槽位可以部分继承）
    SAME_DOMAIN_INTENTS = {
        'query_packages': {'query_package_detail', 'change_package'},
        'query_current_package': {'query_usage', 'change_package'},
        'query_package_detail': {'query_packages', 'change_package'}
    }

    def fill_slots(self,
                   current_slots: Dict[str, Any],
                   new_slots: Dict[str, Any],
                   current_intent: str,
                   new_intent: str) -> Dict[str, Any]:
        """
        填充槽位

        Args:
            current_slots: 当前槽位
            new_slots: 新槽位
            current_intent: 当前意图
            new_intent: 新意图

        Returns:
            合并后的槽位
        """
        intent_changed = (current_intent != new_intent)

        if not intent_changed:
            # 意图不变，完全合并
            result = {**current_slots, **new_slots}
            logger.debug(f"意图不变，合并槽位: {list(new_slots.keys())}")

        elif self._is_same_domain(current_intent, new_intent):
            # 相同领域，保留用户信息 + 部分业务槽位
            preserved_slots = {
                k: v for k, v in current_slots.items()
                if k in self.USER_INFO_SLOTS or self._should_preserve(k, new_intent)
            }
            result = {**preserved_slots, **new_slots}
            logger.debug(f"相同领域，保留槽位: {list(preserved_slots.keys())}")

        else:
            # 不同领域，仅保留用户信息
            user_slots = {
                k: v for k, v in current_slots.items()
                if k in self.USER_INFO_SLOTS
            }
            result = {**user_slots, **new_slots}
            logger.debug(f"不同领域，仅保留用户信息: {list(user_slots.keys())}")

        return result

    def _is_same_domain(self, intent1: str, intent2: str) -> bool:
        """判断两个意图是否属于同一领域"""
        if not intent1 or not intent2:
            return False

        return (intent2 in self.SAME_DOMAIN_INTENTS.get(intent1, set()) or
                intent1 in self.SAME_DOMAIN_INTENTS.get(intent2, set()))

    def _should_preserve(self, slot_name: str, new_intent: str) -> bool:
        """判断槽位是否应该保留"""
        # 可以根据具体业务逻辑扩展
        # 例如：查询套餐时的价格范围，在切换到办理套餐时也可能有用
        preserve_rules = {
            'query_packages': {'price_max', 'price_min', 'data_min'},
            'change_package': {'package_name'}
        }

        return slot_name in preserve_rules.get(new_intent, set())

    def validate_slots(self,
                       slots: Dict[str, Any],
                       required_slots: List[str]) -> List[str]:
        """
        验证槽位完整性

        Args:
            slots: 当前槽位
            required_slots: 必填槽位列表

        Returns:
            缺失的槽位列表
        """
        missing = []
        for slot in required_slots:
            if slot not in slots or slots[slot] is None or slots[slot] == "":
                missing.append(slot)

        if missing:
            logger.info(f"缺失槽位: {missing}")

        return missing

    def clear_slots(self, slots: Dict[str, Any], keep_user_info: bool = True) -> Dict[str, Any]:
        """
        清空槽位

        Args:
            slots: 当前槽位
            keep_user_info: 是否保留用户信息

        Returns:
            清空后的槽位
        """
        if keep_user_info:
            result = {
                k: v for k, v in slots.items()
                if k in self.USER_INFO_SLOTS
            }
            logger.info(f"清空槽位，保留用户信息: {list(result.keys())}")
            return result

        logger.info("清空所有槽位")
        return {}

    def merge_slots(self, *slot_dicts: Dict[str, Any]) -> Dict[str, Any]:
        """合并多个槽位字典，后面的覆盖前面的"""
        result = {}
        for slots in slot_dicts:
            result.update(slots)
        return result