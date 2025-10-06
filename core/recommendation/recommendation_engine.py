"""
推荐引擎
"""
from typing import Dict, Any, Optional, List
from core.dst.dialog_state import DialogState
from utils.logger import logger


class RecommendationEngine:
    """推荐引擎"""

    def __init__(self):
        """初始化推荐引擎"""
        logger.info("推荐引擎初始化完成")

    def recommend(self,
                  state: DialogState,
                  query_result: Dict) -> Optional[Dict]:
        """
        生成推荐

        Args:
            state: 对话状态
            query_result: 查询结果

        Returns:
            Optional[Dict]: 推荐信息
        """
        # 检查是否需要推荐
        if not self._should_recommend(query_result):
            return None

        # 提取用户特征
        user_features = self._extract_features(state)

        # 获取候选套餐
        candidates = query_result.get("data", [])
        if not candidates:
            return None

        # 计算推荐分数
        scored_packages = []
        for package in candidates:
            score = self._calculate_score(package, user_features)
            scored_packages.append((package, score))

        # 排序选择最佳
        scored_packages.sort(key=lambda x: x[1], reverse=True)
        best_package, best_score = scored_packages[0]

        # 生成推荐理由
        reason = self._explain_recommendation(best_package, user_features)

        logger.info(f"[Recommendation] 推荐: {best_package['name']}, 分数: {best_score:.2f}")

        return {
            "package": best_package,
            "reason": reason,
            "confidence": min(best_score / 100, 1.0),
            "alternatives": [pkg for pkg, _ in scored_packages[1:3]]  # 备选
        }

    def _should_recommend(self, query_result: Dict) -> bool:
        """
        判断是否需要推荐

        Args:
            query_result: 查询结果

        Returns:
            bool: 是否需要推荐
        """
        count = query_result.get("count", 0)
        # 结果在2-10个之间时推荐
        return 2 <= count <= 10

    def _extract_features(self, state: DialogState) -> Dict[str, Any]:
        """
        提取用户特征

        Args:
            state: 对话状态

        Returns:
            Dict: 用户特征
        """
        features = {}

        # 价格偏好
        if "price_max" in state.slots:
            features["price_preference"] = float(state.slots["price_max"])
        elif "price_min" in state.slots:
            features["price_preference"] = float(state.slots["price_min"]) * 1.5

        # 流量需求
        if "data_min" in state.slots:
            features["data_usage"] = int(state.slots["data_min"])

        # 用户类型
        if state.slots.get("target_user") == "在校生":
            features["is_student"] = True

        # 历史偏好
        if state.user_profile:
            features["previous_package"] = state.user_profile.get("current_package")

        return features

    def _calculate_score(self, package: Dict, features: Dict) -> float:
        """
        计算推荐分数

        Args:
            package: 套餐信息
            features: 用户特征

        Returns:
            float: 推荐分数 (0-100)
        """
        score = 0.0

        # 1. 价格匹配度 (权重40%)
        if "price_preference" in features:
            price_diff = abs(package["price"] - features["price_preference"])
            price_score = max(0, 100 - price_diff)
            score += price_score * 0.4

        # 2. 流量匹配度 (权重30%)
        if "data_usage" in features:
            if package["data_gb"] >= features["data_usage"]:
                # 满足需求
                data_score = 100
                # 但不要过度（浪费）
                if package["data_gb"] > features["data_usage"] * 2:
                    data_score = 70
            else:
                # 不满足需求，严重扣分
                data_score = 30
            score += data_score * 0.3

        # 3. 性价比 (权重20%)
        cpp = package["price"] / package["data_gb"]  # cost per GB
        # 性价比越高分数越高
        cpp_score = max(0, 100 - cpp * 10)
        score += cpp_score * 0.2

        # 4. 用户类型匹配 (权重10%)
        if features.get("is_student"):
            if package["target_user"] == "在校生":
                score += 100 * 0.1
            else:
                score += 50 * 0.1

        return score

    def _explain_recommendation(self, package: Dict, features: Dict) -> str:
        """
        解释推荐理由

        Args:
            package: 套餐信息
            features: 用户特征

        Returns:
            str: 推荐理由
        """
        reasons = []

        # 价格合适
        if "price_preference" in features:
            if abs(package["price"] - features["price_preference"]) < 20:
                reasons.append("价格符合您的预算")

        # 流量充足
        if "data_usage" in features:
            if package["data_gb"] >= features["data_usage"]:
                reasons.append("流量满足您的需求")

        # 性价比高
        cpp = package["price"] / package["data_gb"]
        if cpp < 2:
            reasons.append("性价比很高")

        # 学生优惠
        if features.get("is_student") and package["target_user"] == "在校生":
            reasons.append("学生专享优惠")

        if reasons:
            return "推荐理由: " + "、".join(reasons)
        else:
            return "这个套餐比较适合您"
