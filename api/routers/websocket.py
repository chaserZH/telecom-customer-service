"""
WebSocket路由
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
from core import TelecomChatbotPolicy
from utils import logger

router = APIRouter()
chatbot = TelecomChatbotPolicy()


# 连接管理器
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info(f"WebSocket连接: {client_id}")

    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info(f"WebSocket断开: {client_id}")

    async def send_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(
                json.dumps(message, ensure_ascii=False)
            )

    async def send_direct_message(self, websocket: WebSocket, message: dict):
        """直接向WebSocket发送消息（用于连接建立时）"""
        await websocket.send_text(json.dumps(message, ensure_ascii=False))


manager = ConnectionManager()


@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket聊天"""
    client_id = str(uuid.uuid4())  # 立即生成客户端ID

    try:
        # 使用管理器建立连接
        await manager.connect(websocket, client_id)

        # 发送欢迎消息
        await manager.send_direct_message(websocket, {
            "type": "system",
            "content": "连接成功！有什么可以帮您的吗？",
            "timestamp": datetime.now().isoformat(),
            "client_id": client_id
        })

        logger.info(f"WebSocket客户端 {client_id} 已连接，等待消息...")

        # 消息循环
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)

            logger.info(f"WebSocket收到来自 {client_id} 的消息: {message}")

            # 提取参数
            user_message = message.get("content", "").strip()
            session_id = message.get("session_id", client_id)

            if not user_message:
                await manager.send_message({
                    "type": "error",
                    "content": "消息内容不能为空",
                    "timestamp": datetime.now().isoformat()
                }, client_id)
                continue

            # 调用对话引擎
            try:
                result = chatbot.chat(
                    user_input=user_message,
                    session_id=session_id
                )

                # 发送响应
                await manager.send_message({
                    "type": "response",
                    "session_id": result.get("session_id", session_id),
                    "content": result.get("response", "抱歉，我暂时无法处理您的请求"),
                    "action": result.get("action", ""),
                    "intent": result.get("intent", ""),
                    "timestamp": result.get("metadata", {}).get("timestamp", datetime.now().isoformat())
                }, client_id)

            except Exception as e:
                logger.error(f"对话引擎错误: {e}", exc_info=True)
                await manager.send_message({
                    "type": "error",
                    "content": "系统处理消息时出现错误，请稍后重试",
                    "timestamp": datetime.now().isoformat()
                }, client_id)

    except WebSocketDisconnect:
        logger.info(f"WebSocket客户端 {client_id} 断开连接")
        manager.disconnect(client_id)

    except json.JSONDecodeError:
        logger.error(f"WebSocket消息JSON解析错误 from {client_id}")
        await manager.send_direct_message(websocket, {
            "type": "error",
            "content": "消息格式错误，请发送有效的JSON数据",
            "timestamp": datetime.now().isoformat()
        })
        manager.disconnect(client_id)

    except Exception as e:
        logger.error(f"WebSocket错误 from {client_id}: {e}", exc_info=True)
        manager.disconnect(client_id)