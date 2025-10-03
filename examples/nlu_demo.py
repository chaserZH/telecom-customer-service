"""
第一阶段演示程序
"""
from core import TelecomChatbotNlu


def print_separator():
    """打印分隔线"""
    print("\n" + "=" * 70 + "\n")


def print_response(response: dict):
    """打印响应"""
    print(f"系统回复:\n{response['response']}\n")
    print(f"[调试信息]")
    print(f"  会话ID: {response['session_id']}")
    print(f"  意图: {response['intent']}")
    if response.get('function'):
        print(f"  调用函数: {response['function']}")
        print(f"  参数: {response.get('parameters', {})}")
    if response.get('missing_slots'):
        print(f"  缺失参数: {response['missing_slots']}")


def demo_conversation_1():
    """演示1: 查询便宜的套餐"""
    print_separator()
    print("【演示1: 查询便宜的套餐】")
    print_separator()

    chatbot = TelecomChatbotNlu()

    user_input = "我想看看有没有便宜点的套餐"
    print(f"用户: {user_input}")
    print()

    response = chatbot.chat(user_input)
    print_response(response)


def demo_conversation_2():
    """演示2: 多轮对话 - 查询当前套餐"""
    print_separator()
    print("【演示2: 多轮对话 - 查询当前套餐】")
    print_separator()

    chatbot = TelecomChatbotNlu()
    session_id = "demo_session_002"

    # 第一轮: 用户询问但未提供手机号
    user_input_1 = "帮我查下我现在用的是什么套餐"
    print(f"用户: {user_input_1}")
    print()

    response_1 = chatbot.chat(user_input_1, session_id=session_id)
    print_response(response_1)

    print_separator()

    # 第二轮: 用户补充手机号
    user_input_2 = "13800138000"
    print(f"用户: {user_input_2}")
    print()

    response_2 = chatbot.chat(user_input_2, session_id=session_id)
    print_response(response_2)


def demo_conversation_3():
    """演示3: 复杂条件查询"""
    print_separator()
    print("【演示3: 复杂条件查询】")
    print_separator()

    chatbot = TelecomChatbotNlu()

    user_input = "我每个月话费太贵了,有100块以内的套餐吗"
    print(f"用户: {user_input}")
    print()

    response = chatbot.chat(user_input)
    print_response(response)


def demo_conversation_4():
    """演示4: 多条件查询"""
    print_separator()
    print("【演示4: 多条件查询】")
    print_separator()

    chatbot = TelecomChatbotNlu()

    user_input = "月费200以下的,流量至少50G"
    print(f"用户: {user_input}")
    print()

    response = chatbot.chat(user_input)
    print_response(response)


def demo_conversation_5():
    """演示5: 业务咨询(RAG预留接口)"""
    print_separator()
    print("【演示5: 业务咨询 - RAG预留接口】")
    print_separator()

    chatbot = TelecomChatbotNlu()

    user_input = "有什么优惠活动吗"
    print(f"用户: {user_input}")
    print()

    response = chatbot.chat(user_input)
    print_response(response)


def interactive_mode():
    """交互式模式"""
    print_separator()
    print("【交互式对话模式】")
    print("输入 'quit' 或 'exit' 退出")
    print_separator()

    chatbot = TelecomChatbotNlu()
    session_id = "interactive_session"

    while True:
        try:
            user_input = input("\n用户: ").strip()

            if user_input.lower() in ['quit', 'exit', '退出']:
                print("再见!")
                break

            if not user_input:
                continue

            response = chatbot.chat(user_input, session_id=session_id)
            print(f"\n系统: {response['response']}")

        except KeyboardInterrupt:
            print("\n\n再见!")
            break
        except Exception as e:
            print(f"\n发生错误: {e}")


def main():
    """主函数"""
    print("\n" + "=" * 70)
    print(" " * 15 + "电信套餐AI智能客服系统 - 第一阶段演示")
    print("=" * 70)

    # 运行各个演示
    demo_conversation_1()
    demo_conversation_2()
    demo_conversation_3()
    demo_conversation_4()
    demo_conversation_5()

    # 询问是否进入交互模式
    print_separator()
    choice = input("是否进入交互式对话模式? (y/n): ").strip().lower()
    if choice == 'y':
        interactive_mode()

    print_separator()
    print("演示结束!")


if __name__ == "__main__":
    main()