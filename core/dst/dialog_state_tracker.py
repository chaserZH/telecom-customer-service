"""
对话状态跟踪器（修复版）
"""
from typing import Optional
from datetime import datetime

from core.dst.StateManager import StateManager
from core.dst.dialog_state import DialogState, DialogTurn
from core.dst.state_store import StateStore

from core.dst.slot_manager import SlotManager
from core.dst.context_manager import ContextManager
from core.nlu.function_definitions import get_required_params
from utils import logger


class DialogStateTracker:
    """对话状态跟踪器"""

    def __init__(self):
        """初始化"""
        self.state_store = StateStore()
        self.state_manager = StateManager()
        self.slot_manager = SlotManager()
        self.context_manager = ContextManager()

        logger.info("对话状态跟踪器初始化完成")

    def track(self, session_id: str, nlu_result) -> DialogState:
        """
        跟踪对话状态

        Args:
            session_id: 会话ID
            nlu_result: NLU解析结果

        Returns:
            更新后的对话状态
        """
        logger.info(f"[DST] 开始跟踪会话: {session_id}")

        # 1. 加载旧状态
        old_state = self.state_store.load(session_id)

        # 2. 检查是否过期
        if self.state_manager.is_state_expired(old_state):
            logger.info(f"会话已过期，重新初始化: {session_id}")
            old_state = self.state_manager.initialize_state(session_id)

        # 🔥 2.5. 检查待确认状态是否超时
        if old_state.is_confirmation_expired():
            logger.warning(f"待确认操作已超时，自动清除")
            old_state.clear_pending_confirmation()

        # 3. 添加用户输入到历史
        if hasattr(nlu_result, 'raw_input') and nlu_result.raw_input:
            old_state.add_turn('user', nlu_result.raw_input, nlu_result.intent)

        # 4. 判断意图是否改变
        new_intent = nlu_result.intent
        intent_changed = (old_state.current_intent != new_intent)

        if intent_changed:
            logger.info(f"意图改变: {old_state.current_intent} → {new_intent}")

        # 🔥 4.5. 如果意图改变且存在待确认状态，判断是否清除
        if intent_changed and old_state.pending_confirmation:
            should_clear = self._should_clear_pending_confirmation(
                old_state.confirmation_intent,  # 使用待确认的意图
                new_intent
            )

            if should_clear:
                logger.info(f"意图改变到不相关领域: {old_state.confirmation_intent} → {new_intent}, "
                           f"清除待确认状态")
                old_state.clear_pending_confirmation()
            else:
                logger.info(f"意图改变但相关联: {old_state.confirmation_intent} → {new_intent}, "
                           f"保留待确认状态")

        # 5. 更新槽位
        new_slots = self.slot_manager.fill_slots(
            old_state.slots,
            nlu_result.parameters,
            old_state.current_intent or "",
            new_intent
        )

        # 6. 从上下文补全槽位
        if intent_changed:
            context_entities = self.context_manager.extract_entities_from_context(
                old_state.context_stack
            )
            # 补全用户信息槽位
            for key in ['phone', 'name']:
                if key not in new_slots and key in context_entities:
                    new_slots[key] = context_entities[key]
                    logger.debug(f"从上下文补全槽位: {key}")

        # 7. 更新上下文
        new_context = self.context_manager.update_context(
            old_state.context_stack,
            nlu_result
        )

        # 8. 构建新状态
        new_state = DialogState(
            session_id=session_id,
            user_phone=new_slots.get('phone') or old_state.user_phone,
            user_name=new_slots.get('name') or old_state.user_name,
            current_intent=new_intent,
            previous_intent=old_state.current_intent,
            slots=new_slots,
            history=old_state.history,
            context_stack=new_context,
            turn_count=old_state.turn_count,
            created_at=old_state.created_at,
            updated_at=datetime.now(),
            user_profile=old_state.user_profile,
            # 🔥 保留待确认状态（如果没被清除）
            pending_confirmation=old_state.pending_confirmation,
            confirmation_intent=old_state.confirmation_intent,
            confirmation_slots=old_state.confirmation_slots,
            confirmation_timestamp=old_state.confirmation_timestamp
        )

        # 9. 验证槽位完整性
        self._validate_slots(new_state)

        # 10. 验证状态有效性
        if not self.state_manager.validate_state(new_state):
            logger.error(f"状态验证失败: {session_id}")

        # 11. 保存状态
        self.state_store.save(session_id, new_state)

        logger.info(f"[DST] 状态跟踪完成: turn={new_state.turn_count}, "
                    f"需要澄清={new_state.needs_clarification}, "
                    f"待确认={new_state.pending_confirmation}")

        return new_state

    def _should_clear_pending_confirmation(self,
                                          old_intent: str,
                                          new_intent: str) -> bool:
        """
        判断是否应该清除待确认状态

        策略：
        1. 如果新意图是 chat/闲聊，保留（可能只是随口问一句）
        2. 如果新旧意图属于同一业务领域，保留
        3. 其他情况，清除

        Args:
            old_intent: 旧意图（待确认的意图）
            new_intent: 新意图

        Returns:
            bool: 是否应该清除
        """
        # 规则1: chat/闲聊不清除
        if new_intent in ["chat", "greeting", "thanks"]:
            return False

        # 规则2: 同业务领域不清除
        intent_domains = {
            "package": ["query_packages", "query_package_detail",
                       "change_package", "query_current_package"],
            "usage": ["query_usage", "query_balance"],
            "consult": ["business_consultation"]
        }

        old_domain = self._get_intent_domain(old_intent, intent_domains)
        new_domain = self._get_intent_domain(new_intent, intent_domains)

        if old_domain and old_domain == new_domain:
            logger.debug(f"意图属于同一领域: {old_domain}")
            return False  # 同领域，保留

        # 规则3: 其他情况清除
        logger.debug(f"意图跨领域: {old_domain} → {new_domain}")
        return True

    def _get_intent_domain(self, intent: str, domains: dict) -> Optional[str]:
        """获取意图所属领域"""
        for domain, intents in domains.items():
            if intent in intents:
                return domain
        return None

    def _validate_slots(self, state: DialogState):
        """验证槽位完整性"""
        if not state.current_intent:
            return

        # 获取必填槽位
        required_slots = get_required_params(state.current_intent)

        # 检查缺失
        missing_slots = self.slot_manager.validate_slots(
            state.slots,
            required_slots
        )

        if missing_slots:
            state.needs_clarification = True
            state.missing_slots = missing_slots
            logger.info(f"缺失必填槽位: {missing_slots}")
        else:
            state.needs_clarification = False
            state.missing_slots = []

    def get_state(self, session_id: str) -> DialogState:
        """
        获取对话状态

        Args:
            session_id: 会话ID

        Returns:
            对话状态
        """
        return self.state_store.load(session_id)

    def reset_state(self, session_id: str):
        """
        重置对话状态

        Args:
            session_id: 会话ID
        """
        self.state_store.delete(session_id)
        logger.info(f"重置会话状态: {session_id}")

    def update_user_info(self, session_id: str, phone: Optional[str] = None,
                         name: Optional[str] = None):
        """
        更新用户信息

        Args:
            session_id: 会话ID
            phone: 手机号
            name: 姓名
        """
        state = self.state_store.load(session_id)

        if phone:
            state.user_phone = phone
            state.slots['phone'] = phone

        if name:
            state.user_name = name
            state.slots['name'] = name

        state.updated_at = datetime.now()
        self.state_store.save(session_id, state)

        logger.info(f"更新用户信息: session={session_id}, phone={phone}, name={name}")