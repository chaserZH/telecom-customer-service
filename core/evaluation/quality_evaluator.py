"""
对话质量评估器
"""
from typing import Dict
from core.dst.dialog_state import DialogState
from utils.logger import logger


class DialogQualityEvaluator:
    """对话质量评估器"""

    # 最优轮次映射
    OPTIMAL_TURNS = {
        "query_packages": 2,
        "query_current_package": 2,
        "query_package_detail": 2,
        "change_package": 3,
        "query_usage": 2,
        "business_consultation": 3
    }

    def __init__(self):
        """初始化评估器"""
        logger.info("质量评估器初始化完成")

    def evaluate(self, state: DialogState) -> Dict:
        """
        评估对话质量

        Args:
            state: 对话状态

        Returns:
            Dict: 评估指标
        """
        metrics = {
            "task_success": self._eval_task_success(state),
            "efficiency": self._eval_efficiency(state),
            "user_satisfaction": self._eval_satisfaction(state),
            "response_quality": self._eval_response_quality(state)
        }

        # 计算总分
        metrics["overall_score"] = self._calculate_overall(metrics)

        logger.info(f"[Evaluation] 对话质量: {metrics['overall_score']:.2f}")

        return metrics

    def _eval_task_success(self, state: DialogState) -> float:
        """
        评估任务成功率

        Args:
            state: 对话状态

        Returns:
            float: 成功率分数 (0-1)
        """
        if state.is_completed:
            return 1.0
        elif state.current_intent and not state.needs_clarification:
            return 0.7
        elif state.current_intent:
            return 0.5
        return 0.0

    def _eval_efficiency(self, state: DialogState) -> float:
        """
        评估对话效率

        Args:
            state: 对话状态

        Returns:
            float: 效率分数 (0-1)
        """
        optimal = self.OPTIMAL_TURNS.get(state.current_intent, 3)
        actual = state.turn_count

        if actual <= optimal:
            return 1.0
        else:
            # 每多一轮扣10%
            penalty = (actual - optimal) * 0.1
            return max(0, 1.0 - penalty)

    def _eval_satisfaction(self, state: DialogState) -> float:
        """
        评估用户满意度（基于行为）

        Args:
            state: 对话状态

        Returns:
            float: 满意度分数 (0-1)
        """
        score = 1.0

        # 检查是否有重复询问
        if self._has_repetition(state):
            score -= 0.2

        # 检查是否有错误
        if self._has_errors(state):
            score -= 0.3

        # 检查轮次是否过多
        if state.turn_count > 10:
            score -= 0.2

        return max(0, score)

    def _eval_response_quality(self, state: DialogState) -> float:
        """
        评估响应质量

        Args:
            state: 对话状态

        Returns:
            float: 响应质量分数 (0-1)
        """
        # 简化版本：基于是否有完整回复
        if state.history:
            assistant_turns = [t for t in state.history if t.role == "assistant"]
            if assistant_turns:
                avg_length = sum(len(t.content) for t in assistant_turns) / len(assistant_turns)
                # 回复长度在50-300之间为最佳
                if 50 <= avg_length <= 300:
                    return 1.0
                elif avg_length < 50:
                    return 0.7
                else:
                    return 0.8
        return 0.5

    def _has_repetition(self, state: DialogState) -> bool:
        """检查是否有重复询问"""
        if len(state.history) < 4:
            return False

        # 检查最近的询问是否重复
        assistant_messages = [t.content for t in state.history if t.role == "assistant"]
        if len(assistant_messages) >= 2:
            # 简单检查：相似度
            last_two = assistant_messages[-2:]
            if last_two[0] == last_two[1]:
                return True

        return False

    def _has_errors(self, state: DialogState) -> bool:
        """检查是否有错误"""
        # 检查历史中是否有致歉
        for turn in state.history:
            if turn.role == "assistant" and "抱歉" in turn.content:
                return True
        return False

    def _calculate_overall(self, metrics: Dict) -> float:
        """
        计算总分

        Args:
            metrics: 各项指标

        Returns:
            float: 总分 (0-100)
        """
        weights = {
            "task_success": 0.4,
            "efficiency": 0.3,
            "user_satisfaction": 0.2,
            "response_quality": 0.1
        }

        overall = sum(
            metrics[key] * weights[key]
            for key in weights.keys()
        )

        return overall * 100

