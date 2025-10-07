# tests/test_api.py
import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_chat_api():
    """测试聊天API"""
    response = client.post("/api/chat", json={
        "message": "有100元以内的套餐吗"
    })

    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "response" in data
    assert len(data["response"]) > 0


def test_session_api():
    """测试会话API"""
    # 创建会话
    chat_response = client.post("/api/chat", json={
        "message": "你好"
    })
    session_id = chat_response.json()["session_id"]

    # 获取会话状态
    session_response = client.get(f"/api/session/{session_id}")
    assert session_response.status_code == 200

    # 重置会话
    reset_response = client.delete(f"/api/session/{session_id}")
    assert reset_response.status_code == 200