# tests/test_nlu_improved.py
"""
测试改进后的NLU引擎
"""
from core.nlu import NLUEngine


def test_rule_matching():
    """测试规则前置"""
    nlu = NLUEngine()

    # 测试用例
    test_cases = [
        ("我要办理经济套餐", "change_package", "rule"),
        ("我要办理套餐", "query_packages", "rule"),
        ("怎么办理套餐", "business_consultation", "rule"),
        ("我的套餐是什么", "query_current_package", "rule"),
        ("100元以内的套餐", "query_packages", "rule"),
        ("办理流程", "business_consultation", "rule"),
    ]

    for user_input, expected_intent, expected_source in test_cases:
        result = nlu.understand(user_input, "test_session")

        print(f"\n输入: {user_input}")
        print(f"意图: {result.intent} (期望: {expected_intent})")
        print(f"来源: {result.source} (期望: {expected_source})")
        print(f"参数: {result.parameters}")
        print(f"置信度: {result.confidence:.2f}")

        assert result.intent == expected_intent, f"意图不匹配: {result.intent} != {expected_intent}"
        print("✓ 测试通过")


def test_llm_fallback():
    """测试LLM兜底"""
    nlu = NLUEngine()

    # 复杂场景（规则无法覆盖）
    complex_cases = [
        "帮我看看有没有适合学生用的，而且价格不要太贵的套餐",
        "我想换个套餐，流量要多一点，但是价格要便宜",
    ]

    for user_input in complex_cases:
        result = nlu.understand(user_input, "test_complex")

        print(f"\n输入: {user_input}")
        print(f"意图: {result.intent}")
        print(f"来源: {result.source}")
        print(f"参数: {result.parameters}")


def test_post_validation():
    """测试后验证"""
    nlu = NLUEngine()

    # 模拟LLM返回错误结果
    session_id = "test_validation"

    # 场景1: "我要办理套餐"应该是query_packages而不是change_package
    # result = nlu.understand("我要办理套餐", session_id)
    # print(f"\n场景1: 无具体套餐名的办理")
    # print(f"意图: {result.intent} (应为query_packages)")
    # print(f"来源: {result.source}")
    #
    # # 场景2: "怎么办理套餐"应该是business_consultation
    # result = nlu.understand("怎么办理套餐", session_id)
    # print(f"\n场景2: 咨询办理")
    # print(f"意图: {result.intent} (应为business_consultation)")
    # print(f"来源: {result.source}")
    # # 场景2: "怎么办理套餐"应该是business_consultation
    result = nlu.understand("我要办理经济套餐", session_id)
    print(f"\n场景3: 咨询办理")
    print(f"意图: {result.intent} (应为change_package)")
    print(f"来源: {result.source}")


if __name__ == "__main__":
    print("=" * 60)
    print("测试1: 规则前置")
    print("=" * 60)
    test_rule_matching()

    print("\n" + "=" * 60)
    print("测试2: LLM兜底")
    print("=" * 60)
    test_llm_fallback()

    print("\n" + "=" * 60)
    print("测试3: 后验证")
    print("=" * 60)
    test_post_validation()