# tests/test_websocket.py
import pytest
from fastapi.testclient import TestClient
from api.main import app
import json


def test_websocket_chat():
    """测试WebSocket聊天"""
    with TestClient(app).websocket_connect("/ws/chat") as websocket:
        # 接收欢迎消息
        data = websocket.receive_json()
        assert data["type"] == "system"

        # 发送消息
        websocket.send_json({
            "type": "message",
            "content": "有什么套餐"
        })

        # 接收响应
        response = websocket.receive_json()
        assert response["type"] == "response"
        assert "content" in response