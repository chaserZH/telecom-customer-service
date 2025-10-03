# -*- coding: utf-8 -*-
"""
第二阶段演示程序 - DST模块
"""


import json

from core import TelecomChatbotDst


def print_separator():
    """打印分隔线"""
    print("\n" + "=" * 70 + "\n")


def print_response(response: dict):
    """打印响应"""
    print(f"系统回复:\n{response['response']}\n")
    print(f"[调试信息]")
    print(f"  会话ID: {response['session_id']}")
    print(f"  意图: {response['intent']}")
    print(f"  需要补充: {response.get('requires_input', False)}")

    if response.get('missing_slots'):
        print(f"  缺失槽位: {response['missing_slots']}")

    # 显示状态信息
    if 'state' in response:
        state = response['state']
        print(f"\n[状态信息]")
        print(f"  轮次: {state['turn_count']}")
        print(f"  当前意图: {state['current_intent']}")
        print(f"  槽位: {json.dumps(state['slots'], ensure_ascii=False)}")


def demo_multi_turn_with_dst():
    """演示1: DST支持的复杂多轮对话"""
    print_separator()
    print("【演示1: DST支持的复杂多轮对话】")
    print_separator()

    chatbot = TelecomChatbotDst()
    session_id = "demo_dst_001"

    # 第一轮: 查询套餐
    print("第1轮:")
    response1 = chatbot.chat("有100元以内的套餐吗", session_id=session_id)
    print_response(response1)

    print_separator()

    # 第二轮: 继续添加条件（DST会自动继承price_max）
    print("第2轮:")
    response2 = chatbot.chat("流量要50G以上", session_id=session_id)
    print_response(response2)

    print_separator()

    # 第三轮: 切换意图，查询自己的套餐（phone应该不需要重新问）
    print("第3轮:")
    response3 = chatbot.chat("我用的是什么套餐", session_id=session_id)
    print_response(response3)


def demo_slot_inheritance():
    """演示2: 槽位继承"""
    print_separator()
    print("【演示2: 槽位智能继承】")
    print_separator()

    chatbot = TelecomChatbotDst()
    session_id = "demo_dst_002"

    # 设置用户手机号
    print("第1轮: 查询当前套餐（需要手机号）")
    response1 = chatbot.chat("查下我的套餐", session_id=session_id)
    print_response(response1)

    print_separator()

    print("第2轮: 提供手机号")
    response2 = chatbot.chat("13800138000", session_id=session_id)
    print_response(response2)

    print_separator()

    print("第3轮: 查询使用情况（phone应该自动继承）")
    response3 = chatbot.chat("我用了多少流量", session_id=session_id)
    print_response(response3)

    # 检查是否自动继承了phone
    if not response3.get('requires_input'):
        print("\n✅ 成功！phone槽位已自动继承，无需重新询问")
    else:
        print("\n❌ 失败！phone槽位未继承")


def demo_context_management():
    """演示3: 上下文管理"""
    print_separator()
    print("【演示3: 上下文管理】")
    print_separator()

    chatbot = TelecomChatbotDst()
    session_id = "demo_dst_003"

    conversations = [
        "有什么便宜的套餐",
        "100元以内的",
        "流量要多一点",
        "至少50G吧",
        "算了，给我看看所有套餐"
    ]

    for i, user_input in enumerate(conversations, 1):
        print(f"第{i}轮:")
        print(f"用户: {user_input}")
        response = chatbot.chat(user_input, session_id=session_id)
        print(f"系统: {response['response'][:100]}...")
        print(f"当前槽位: {response.get('state', {}).get('slots', {})}")
        print()


def demo_state_persistence():
    """演示4: 状态持久化（Redis）"""
    print_separator()
    print("【演示4: 状态持久化】")
    print_separator()

    chatbot = TelecomChatbotDst()
    session_id = "demo_persist_001"

    # 第一次对话
    print("第1次对话:")
    response1 = chatbot.chat("有100元以内的套餐吗", session_id=session_id)
    print(f"系统: {response1['response'][:80]}...")

    print("\n[模拟应用重启...]\n")

    # 创建新的chatbot实例（模拟重启）
    chatbot2 = TelecomChatbotDst()

    # 继续对话（应该能恢复状态）
    print("第2次对话（重启后）:")
    response2 = chatbot2.chat("流量要50G以上", session_id=session_id)
    print(f"系统: {response2['response'][:80]}...")

    # 检查状态是否恢复
    state = response2.get('state', {})
    if 'price_max' in state.get('slots', {}):
        print("\n✅ 成功！状态已从Redis恢复，price_max仍然存在")
    else:
        print("\n❌ 失败！状态未恢复")


def interactive_mode_phase2():
    """交互式模式 - Phase2"""
    print_separator()
    print("【交互式对话模式 - 第二阶段（含DST）】")
    print("输入 'quit' 或 'exit' 退出")
    print("输入 'state' 查看当前状态")
    print("输入 'reset' 重置会话")
    print_separator()

    chatbot = TelecomChatbotDst()
    session_id = "interactive_phase2"

    while True:
        try:
            user_input = input("\n用户: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("再见!")
                break

            if user_input.lower() == 'state':
                state = chatbot.get_session_state(session_id)
                print(json.dumps(state, ensure_ascii=False, indent=2))
                continue

            if user_input.lower() == 'reset':
                chatbot.reset_session(session_id)
                print("会话已重置")
                continue

            if not user_input:
                continue

            response = chatbot.chat(user_input, session_id=session_id)
            print(f"\n系统: {response['response']}")

            # 显示简要状态
            if 'state' in response:
                state = response['state']
                print(f"\n[轮次:{state['turn_count']} | 意图:{state['current_intent']} | 槽位数:{len(state['slots'])}]")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print(" " * 10 + "电信套餐AI智能客服系统 - 第二阶段演示（含DST）")
    print("=" * 70)

    # 运行各个演示
    demo_multi_turn_with_dst()
    demo_slot_inheritance()
    demo_context_management()
    demo_state_persistence()

    # 询问是否进入交互模式
    print_separator()
    choice = input("是否进入交互式对话模式? (y/n): ").strip().lower()
    if choice == 'y':
        interactive_mode_phase2()

    print_separator()
    print("演示结束!")


if __name__ == "__main__":
    main()