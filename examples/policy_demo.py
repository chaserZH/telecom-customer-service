"""
第三阶段演示程序 - Policy + NLG模块
"""
import json
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import TelecomChatbotPolicy
from core.evaluation import DialogQualityEvaluator


def print_separator(title="", width=70):
    """打印分隔线"""
    if title:
        print(f"\n{'=' * width}")
        print(f"{title:^{width}}")
        print(f"{'=' * width}\n")
    else:
        print(f"\n{'=' * width}\n")


def print_response(response: dict, show_details: bool = True):
    """打印响应"""
    print(f"系统回复:\n{response['response']}\n")

    if show_details:
        print(f"[调试信息]")
        print(f"  会话ID: {response['session_id']}")
        print(f"  动作类型: {response['action']}")
        print(f"  意图: {response['intent']}")
        print(f"  轮次: {response['state']['turn_count']}")
        print(f"  耗时: {response['metadata']['execution_time_ms']:.0f}ms")

        if response.get('requires_confirmation'):
            print(f"  需要确认: 是")


def demo_1_basic_query():
    """演示1: 基本查询（展示NLG生成）"""
    print_separator("【演示1】基本查询 - NLG模板生成")

    chatbot = TelecomChatbotPolicy()

    # 查询套餐
    print("用户: 有100元以内的套餐吗\n")
    response = chatbot.chat("有100元以内的套餐吗")
    print_response(response)


def demo_2_recommendation():
    """演示2: 智能推荐（展示推荐引擎）"""
    print_separator("【演示2】智能推荐 - 推荐引擎")

    chatbot = TelecomChatbotPolicy()
    session_id = "demo_recommendation"

    # 查询多个套餐，触发推荐
    print("用户: 有什么套餐\n")
    response = chatbot.chat("有什么套餐", session_id=session_id)
    print_response(response)


def demo_3_confirmation_flow():
    """演示3: 确认流程（展示Policy决策）"""
    print_separator("【演示3】确认流程 - Policy决策")

    chatbot = TelecomChatbotPolicy()
    session_id = "demo_confirmation"

    # 第1轮：办理套餐
    print("第1轮:")
    print("用户: 我要办理畅游套餐\n")
    response1 = chatbot.chat("我要办理畅游套餐", session_id=session_id)
    print_response(response1)

    print_separator()

    # 第2轮：提供手机号
    if response1['action'] == 'REQUEST':
        print("第2轮:")
        print("用户: 13800138000\n")
        response2 = chatbot.chat("13800138000", session_id=session_id)
        print_response(response2)

        print_separator()

        # 第3轮：确认
        if response2['action'] == 'CONFIRM':
            print("第3轮:")
            print("用户: 确认\n")
            response3 = chatbot.chat("确认", session_id=session_id)
            print_response(response3)


def demo_4_multi_turn_with_nlg():
    """演示4: 多轮对话（展示完整流程）"""
    print_separator("【演示4】多轮对话 - 完整流程展示")

    chatbot = TelecomChatbotPolicy()
    session_id = "demo_multi_turn"

    conversations = [
        "有便宜的套餐吗",
        "流量要50G以上",
        "那推荐哪个呢",
    ]

    for i, user_input in enumerate(conversations, 1):
        print(f"第{i}轮:")
        print(f"用户: {user_input}\n")

        response = chatbot.chat(user_input, session_id=session_id)
        print(f"系统: {response['response']}")
        print(f"[动作: {response['action']}, 轮次: {response['state']['turn_count']}]\n")

        print_separator()


def demo_5_llm_generation():
    """演示5: LLM生成（对比模板与LLM）"""
    print_separator("【演示5】LLM生成 - 对比模板与LLM")

    chatbot = TelecomChatbotPolicy()
    session_id = "demo_llm"

    print("场景：查询多个套餐，需要推荐")
    print("（此场景会触发LLM生成更自然的推荐话术）\n")

    print("用户: 200元以内的套餐\n")
    response = chatbot.chat("200元以内的套餐", session_id=session_id)
    print_response(response)


def demo_6_error_handling():
    """演示6: 错误处理（展示Policy的错误处理）"""
    print_separator("【演示6】错误处理 - Policy错误处理")

    chatbot = TelecomChatbotPolicy()
    session_id = "demo_error"

    print("用户: 查询不存在的手机号\n")
    response = chatbot.chat("查询123的套餐", session_id=session_id)
    print_response(response)


def demo_7_cache_performance():
    """演示7: 缓存性能（展示缓存优化）"""
    print_separator("【演示7】缓存性能 - 性能优化")

    chatbot = TelecomChatbotPolicy()

    print("第1次请求（未命中缓存）:")
    print("用户: 请提供手机号\n")
    response1 = chatbot.chat("查下我的套餐", session_id="cache_test_1")
    print(f"系统: {response1['response']}")
    print(f"耗时: {response1['metadata']['execution_time_ms']:.0f}ms\n")

    print_separator()

    print("第2次相同请求（可能命中缓存）:")
    print("用户: 请提供手机号\n")
    response2 = chatbot.chat("查下我的套餐", session_id="cache_test_2")
    print(f"系统: {response2['response']}")
    print(f"耗时: {response2['metadata']['execution_time_ms']:.0f}ms\n")

    # 显示缓存统计
    stats = chatbot.get_cache_stats()
    print(f"缓存统计: {stats}")


def demo_8_quality_evaluation():
    """演示8: 质量评估（展示评估器）"""
    print_separator("【演示8】质量评估 - 对话质量评估")

    chatbot = TelecomChatbotPolicy()
    evaluator = DialogQualityEvaluator()
    session_id = "demo_evaluation"

    # 进行一次完整对话
    print("进行对话...")
    chatbot.chat("有100元以内的套餐吗", session_id=session_id)
    chatbot.chat("流量要50G", session_id=session_id)

    # 获取状态并评估
    state = chatbot.dst.get_state(session_id)
    metrics = evaluator.evaluate(state)

    print("\n对话质量评估:")
    print(f"  任务成功率: {metrics['task_success'] * 100:.1f}%")
    print(f"  对话效率: {metrics['efficiency'] * 100:.1f}%")
    print(f"  用户满意度: {metrics['user_satisfaction'] * 100:.1f}%")
    print(f"  回复质量: {metrics['response_quality'] * 100:.1f}%")
    print(f"  综合得分: {metrics['overall_score']:.1f}/100")


def interactive_mode():
    """交互式模式"""
    print_separator("【交互式对话模式】")
    print("命令:")
    print("  quit/exit - 退出")
    print("  state - 查看状态")
    print("  reset - 重置会话")
    print("  eval - 评估质量")
    print("  cache - 缓存统计")
    print_separator()

    chatbot = TelecomChatbotPolicy()
    evaluator = DialogQualityEvaluator()
    session_id = "interactive_session"

    while True:
        try:
            user_input = input("\n用户: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\n再见！")
                break

            if user_input.lower() == 'state':
                state = chatbot.get_session_state(session_id)
                print(json.dumps(state, ensure_ascii=False, indent=2))
                continue

            if user_input.lower() == 'reset':
                chatbot.reset_session(session_id)
                print("✓ 会话已重置")
                continue

            if user_input.lower() == 'eval':
                state = chatbot.dst.get_state(session_id)
                metrics = evaluator.evaluate(state)
                print("\n质量评估:")
                print(f"  综合得分: {metrics['overall_score']:.1f}/100")
                print(f"  任务成功: {metrics['task_success'] * 100:.0f}%")
                print(f"  对话效率: {metrics['efficiency'] * 100:.0f}%")
                continue

            if user_input.lower() == 'cache':
                stats = chatbot.get_cache_stats()
                print(f"\n缓存统计: {stats}")
                continue

            if not user_input:
                continue

            response = chatbot.chat(user_input, session_id=session_id)
            print(f"\n系统: {response['response']}")

            # 显示简要信息
            print(f"\n[{response['action']} | 轮次:{response['state']['turn_count']} | "
                  f"耗时:{response['metadata']['execution_time_ms']:.0f}ms]")

        except KeyboardInterrupt:
            print("\n\n再见！")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print(" " * 15 + "电信套餐AI智能客服系统")
    print(" " * 15 + "第三阶段演示（Policy + NLG）")
    print("=" * 70)

    # 运行所有演示
    demo_1_basic_query()
    demo_2_recommendation()
    demo_3_confirmation_flow()
    demo_4_multi_turn_with_nlg()
    demo_5_llm_generation()
    demo_6_error_handling()
    demo_7_cache_performance()
    demo_8_quality_evaluation()

    # 询问是否进入交互模式
    print_separator()
    choice = input("是否进入交互式对话模式? (y/n): ").strip().lower()
    if choice == 'y':
        interactive_mode()

    print_separator("演示结束")


if __name__ == "__main__":
    main()