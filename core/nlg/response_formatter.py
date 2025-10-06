"""
回复格式化工具
"""
import re

from core.dst.dialog_state import DialogState


class ResponseFormatter:
    """回复格式化器"""

    @staticmethod
    def format_package_list(packages: list, max_display: int = 5) -> str:
        """
        格式化套餐列表

        Args:
            packages: 套餐列表
            max_display: 最多显示数量

        Returns:
            str: 格式化后的文本
        """
        if not packages:
            return ""

        result = []
        for i, pkg in enumerate(packages[:max_display], 1):
            item = f"【{pkg['name']}】\n"
            item += f"  💰 月费: {pkg['price']}元\n"
            item += f"  📊 流量: {pkg['data_gb']}GB/月\n"
            item += f"  📞 通话: {pkg.get('voice_minutes', 0)}分钟/月\n"
            item += f"  👥 适用: {pkg['target_user']}"
            result.append(item)

        text = "\n\n".join(result)

        if len(packages) > max_display:
            text += f"\n\n还有{len(packages) - max_display}个套餐，如需了解请告诉我"

        return text

    @staticmethod
    def truncate(text: str, max_length: int = 500) -> str:
        """
        截断过长文本

        Args:
            text: 原文本
            max_length: 最大长度

        Returns:
            str: 截断后的文本
        """
        if len(text) <= max_length:
            return text

        # 在句号处截断
        sentences = text[:max_length].split('。')
        if len(sentences) > 1:
            return '。'.join(sentences[:-1]) + '。...'

        return text[:max_length] + '...'

    @staticmethod
    def add_guidance(text: str, guidance: str) -> str:
        """
        添加引导语

        Args:
            text: 原文本
            guidance: 引导语

        Returns:
            str: 添加引导后的文本
        """
        if not guidance:
            return text

        return f"{text}\n\n💡 {guidance}"

    @staticmethod
    def add_closing(text: str, state: DialogState) -> str:
        """
        添加结束语

        Args:
            text: 原文本
            state: 对话状态

        Returns:
            str: 添加结束语后的文本
        """
        # 超过3轮对话后添加结束语
        if state.turn_count > 3:
            return f"{text}\n\n还有什么可以帮您的吗？"

        return text

    @staticmethod
    def clean_text(text: str) -> str:
        """
        清理文本

        Args:
            text: 原文本

        Returns:
            str: 清理后的文本
        """
        # 统一换行符
        text = text.replace('\r\n', '\n')

        # 去除多余空行
        text = re.sub(r'\n{3,}', '\n\n', text)

        # emoji前后加空格
        text = re.sub(r'([^\s])([\U0001F300-\U0001F9FF])', r'\1 \2', text)
        text = re.sub(r'([\U0001F300-\U0001F9FF])([^\s])', r'\1 \2', text)

        # 去除首尾空白
        text = text.strip()

        return text

    @staticmethod
    def post_process(text: str, state: DialogState, guidance: str = None) -> str:
        """
        后处理

        Args:
            text: 原文本
            state: 对话状态
            guidance: 引导语

        Returns:
            str: 处理后的文本
        """
        # 1. 长度控制
        text = ResponseFormatter.truncate(text, max_length=500)

        # 2. 添加引导
        if guidance:
            text = ResponseFormatter.add_guidance(text, guidance)

        # 3. 添加结束语
        text = ResponseFormatter.add_closing(text, state)

        # 4. 清理格式
        text = ResponseFormatter.clean_text(text)

        return text
