"""
聊天API路由
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional
from core import TelecomChatbotPolicy
from utils.logger import logger

router = APIRouter()
chatbot = TelecomChatbotPolicy()


# 请求模型
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    user_phone: Optional[str] = None


# 响应模型
class ChatResponse(BaseModel):
    session_id: str
    response: str
    action: str
    intent: str
    requires_confirmation: bool
    data: Optional[dict] = None
    timestamp: str


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """聊天接口"""
    try:
        logger.info(f"收到聊天请求: {request.message}")

        # 调用对话引擎
        result = chatbot.chat(
            user_input=request.message,
            session_id=request.session_id,
            user_phone=request.user_phone
        )

        return ChatResponse(
            session_id=result["session_id"],
            response=result["response"],
            action=result["action"],
            intent=result["intent"],
            requires_confirmation=result.get("requires_confirmation", False),
            data=result.get("data"),
            timestamp=result["metadata"]["timestamp"]
        )

    except Exception as e:
        logger.error(f"聊天处理失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/session/{session_id}")
async def get_session(session_id: str):
    """获取会话状态"""
    try:
        state = chatbot.get_session_state(session_id)
        return {"session_id": session_id, "state": state}
    except Exception as e:
        raise HTTPException(status_code=404, detail="会话不存在")


@router.delete("/session/{session_id}")
async def reset_session(session_id: str):
    """重置会话"""
    try:
        chatbot.reset_session(session_id)
        return {"message": "会话已重置", "session_id": session_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))