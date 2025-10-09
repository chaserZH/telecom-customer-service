# 电信套餐AI智能客服系统 - 第四阶段Web应用设计文档

## 第四阶段概述

### 1.1 阶段目标

**核心目标**：将前三阶段的AI对话能力封装为完整的Web应用，提供可用的用户界面和API服务。

**关键能力**：

1. 🌐 **Web后端**：FastAPI + WebSocket实时通信
2. 💬 **Web前端**：简洁的聊天界面
3. 📡 **API服务**：RESTful API + WebSocket
4. 🚀 **容器化部署**：Docker容器化部署方案

### 1.2 与前三阶段的关系

```tex
第一阶段 (NLU)     →  意图识别、实体抽取
第二阶段 (DST)     →  对话状态跟踪
第三阶段 (Policy)  →  策略决策、回复生成
第四阶段 (Web)     →  Web封装、用户界面 ⭐
```



## 技术架构设计

### 2.1 整体架构图

```
┌─────────────────────────────────────────────────┐
│              用户浏览器                          │
│         (HTML + JavaScript + CSS)               │
└─────────────────────────────────────────────────┘
                    ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────┐
│          FastAPI Web服务器                       │
│  ┌──────────────┐  ┌──────────────┐            │
│  │  HTTP API    │  │  WebSocket   │            │
│  └──────────────┘  └──────────────┘            │
└─────────────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────────────┐
│          核心对话引擎 (已有)                     │
│  TelecomChatbotPolicy (第三阶段)                │
└─────────────────────────────────────────────────┘
                    ↕
┌─────────────────────────────────────────────────┐
│          数据层                                  │
│  MySQL + Redis                                   │
└─────────────────────────────────────────────────┘
```

### 2.2 技术栈选型

| 层级         | 技术选型    | 理由                          |
| ------------ | ----------- | ----------------------------- |
| **后端框架** | FastAPI     | 高性能、异步支持、自动API文档 |
| **实时通信** | WebSocket   | 双向实时通信                  |
| **前端**     | 原生HTML+JS | 简单直接，无需构建工具        |
| **容器化**   | Docker      | 标准化部署                    |



## Web后端设计

### 3.1 FastAPI应用结构

```
api/
├── __init__.py
├── main.py              # FastAPI应用入口
├── routers/
│   ├── __init__.py
│   ├── chat.py         # 聊天API
│   └── websocket.py    # WebSocket路由
├── models/
│   ├── __init__.py
│   └── schemas.py      # Pydantic模型
├── middleware/
│   ├── __init__.py
│   └── cors.py         # CORS中间件
└── static/             # 静态文件
    └── index.html      # 前端页面
```

### 3.2 核心API设计

#### 3.2.1 RESTful API

**1. 聊天接口（HTTP POST）**

```python
POST /api/chat
Content-Type: application/json

Request:
{
    "message": "有100元以内的套餐吗",
    "session_id": "optional-session-id",
    "user_phone": "optional-phone"
}

Response:
{
    "session_id": "uuid-xxx",
    "response": "为您找到1个套餐...",
    "action": "INFORM",
    "intent": "query_packages",
    "requires_confirmation": false,
    "data": {...},
    "timestamp": "2025-10-07T10:00:00Z"
}
```

**2. 会话管理接口**

```python
# 获取会话状态
GET /api/session/{session_id}

# 重置会话
DELETE /api/session/{session_id}

# 获取会话历史
GET /api/session/{session_id}/history
```

#### 3.2.2 WebSocket接口

```python
# WebSocket连接
WS /ws/chat

# 消息格式
Client → Server:
{
    "type": "message",
    "content": "有什么套餐",
    "session_id": "optional"
}

Server → Client:
{
    "type": "response",
    "session_id": "uuid-xxx",
    "content": "为您找到4个套餐...",
    "action": "INFORM",
    "timestamp": "2025-10-07T10:00:00Z"
}
```

### 3.3 核心代码实现

#### 3.3.1 FastAPI主应用 (api/main.py)

```python
"""
FastAPI主应用
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from api.routers import chat, websocket
from utils.logger import logger

# 创建FastAPI应用
app = FastAPI(
    title="电信套餐AI客服系统",
    description="智能对话API",
    version="1.0.0"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(chat.router, prefix="/api", tags=["Chat"])
app.include_router(websocket.router, prefix="/ws", tags=["WebSocket"])

# 静态文件
app.mount("/", StaticFiles(directory="api/static", html=True), name="static")

@app.on_event("startup")
async def startup_event():
    logger.info("FastAPI应用启动成功")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("FastAPI应用关闭")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

#### 3.3.2 聊天API路由 (api/routers/chat.py)

```python
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
```

#### 3.3.3 WebSocket路由 (api/routers/websocket.py)

```python
"""
WebSocket路由
"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import json
from core import TelecomChatbotPolicy
from utils.logger import logger

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

manager = ConnectionManager()

@router.websocket("/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket聊天"""
    client_id = None
    
    try:
        # 接受连接
        await websocket.accept()
        
        # 发送欢迎消息
        await websocket.send_text(json.dumps({
            "type": "system",
            "content": "连接成功！有什么可以帮您的吗？",
            "timestamp": datetime.now().isoformat()
        }, ensure_ascii=False))
        
        # 消息循环
        while True:
            # 接收消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            logger.info(f"WebSocket收到消息: {message}")
            
            # 提取参数
            user_message = message.get("content")
            session_id = message.get("session_id")
            
            if not client_id:
                client_id = session_id or str(uuid.uuid4())
                manager.active_connections[client_id] = websocket
            
            # 调用对话引擎
            result = chatbot.chat(
                user_input=user_message,
                session_id=client_id
            )
            
            # 发送响应
            await manager.send_message({
                "type": "response",
                "session_id": result["session_id"],
                "content": result["response"],
                "action": result["action"],
                "intent": result["intent"],
                "timestamp": result["metadata"]["timestamp"]
            }, client_id)
            
    except WebSocketDisconnect:
        if client_id:
            manager.disconnect(client_id)
        logger.info("WebSocket客户端断开连接")
        
    except Exception as e:
        logger.error(f"WebSocket错误: {e}", exc_info=True)
        if client_id:
            manager.disconnect(client_id)
```

## Web前端设计

### 4.1 简洁聊天界面

#### 4.1.1 界面设计

```python
┌─────────────────────────────────────┐
│  电信套餐AI客服                      │ <- 标题栏
├─────────────────────────────────────┤
│                                     │
│  🤖 系统: 您好！有什么可以帮您？     │
│                                     │
│  👤 用户: 有100元以内的套餐吗        │
│                                     │
│  🤖 系统: 为您找到1个套餐...         │
│                                     │
│  ↓ 聊天消息区域 ↓                    │
│                                     │
├─────────────────────────────────────┤
│ [输入消息...]           [发送]       │ <- 输入栏
└─────────────────────────────────────┘
```

#### 4.1.2 前端代码 (api/static/index.html)

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>电信套餐AI客服</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }

        .chat-container {
            width: 90%;
            max-width: 600px;
            height: 80vh;
            background: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            display: flex;
            flex-direction: column;
        }

        .chat-header {
            background: #667eea;
            color: white;
            padding: 20px;
            border-radius: 12px 12px 0 0;
            text-align: center;
            font-size: 20px;
            font-weight: bold;
        }

        .chat-messages {
            flex: 1;
            overflow-y: auto;
            padding: 20px;
            background: #f5f5f5;
        }

        .message {
            margin-bottom: 15px;
            display: flex;
            align-items: flex-start;
        }

        .message.user {
            flex-direction: row-reverse;
        }

        .message-content {
            max-width: 70%;
            padding: 12px 16px;
            border-radius: 18px;
            line-height: 1.5;
            word-wrap: break-word;
        }

        .message.bot .message-content {
            background: white;
            color: #333;
            border: 1px solid #e0e0e0;
        }

        .message.user .message-content {
            background: #667eea;
            color: white;
        }

        .message-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            margin: 0 10px;
        }

        .message.bot .message-icon {
            background: #667eea;
            color: white;
        }

        .message.user .message-icon {
            background: #764ba2;
            color: white;
        }

        .chat-input {
            display: flex;
            padding: 20px;
            background: white;
            border-radius: 0 0 12px 12px;
            border-top: 1px solid #e0e0e0;
        }

        .chat-input input {
            flex: 1;
            padding: 12px 16px;
            border: 1px solid #e0e0e0;
            border-radius: 24px;
            font-size: 14px;
            outline: none;
        }

        .chat-input input:focus {
            border-color: #667eea;
        }

        .chat-input button {
            margin-left: 10px;
            padding: 12px 24px;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 24px;
            cursor: pointer;
            font-size: 14px;
            transition: background 0.3s;
        }

        .chat-input button:hover {
            background: #5568d3;
        }

        .chat-input button:disabled {
            background: #ccc;
            cursor: not-allowed;
        }

        .typing-indicator {
            display: none;
            padding: 10px;
            color: #999;
            font-style: italic;
        }

        .typing-indicator.active {
            display: block;
        }

        /* 滚动条样式 */
        .chat-messages::-webkit-scrollbar {
            width: 6px;
        }

        .chat-messages::-webkit-scrollbar-track {
            background: #f1f1f1;
        }

        .chat-messages::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 3px;
        }

        .chat-messages::-webkit-scrollbar-thumb:hover {
            background: #555;
        }
    </style>
</head>
<body>
    <div class="chat-container">
        <div class="chat-header">
            电信套餐AI客服
        </div>
        
        <div class="chat-messages" id="chatMessages">
            <div class="message bot">
                <div class="message-icon">🤖</div>
                <div class="message-content">
                    您好！我是电信套餐AI客服，有什么可以帮您的吗？
                </div>
            </div>
        </div>
        
        <div class="typing-indicator" id="typingIndicator">
            AI正在输入...
        </div>
        
        <div class="chat-input">
            <input 
                type="text" 
                id="messageInput" 
                placeholder="输入消息..." 
                autocomplete="off"
            >
            <button id="sendButton">发送</button>
        </div>
    </div>

    <script>
        // WebSocket连接
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const ws = new WebSocket(`${protocol}//${window.location.host}/ws/chat`);
        
        const messagesDiv = document.getElementById('chatMessages');
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        const typingIndicator = document.getElementById('typingIndicator');
        
        let sessionId = null;

        // WebSocket连接成功
        ws.onopen = () => {
            console.log('WebSocket连接成功');
        };

        // 接收消息
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            
            if (data.type === 'system') {
                // 系统消息（连接成功等）
                return;
            }
            
            if (data.type === 'response') {
                sessionId = data.session_id;
                addMessage(data.content, 'bot');
                hideTyping();
            }
        };

        // WebSocket错误
        ws.onerror = (error) => {
            console.error('WebSocket错误:', error);
            addMessage('连接出错，请刷新页面重试', 'bot');
            hideTyping();
        };

        // WebSocket关闭
        ws.onclose = () => {
            console.log('WebSocket连接关闭');
            addMessage('连接已断开，请刷新页面', 'bot');
            hideTyping();
        };

        // 发送消息
        function sendMessage() {
            const message = messageInput.value.trim();
            
            if (!message) return;
            
            // 显示用户消息
            addMessage(message, 'user');
            
            // 清空输入框
            messageInput.value = '';
            
            // 显示输入中提示
            showTyping();
            
            // 通过WebSocket发送
            ws.send(JSON.stringify({
                type: 'message',
                content: message,
                session_id: sessionId
            }));
        }

        // 添加消息到界面
        function addMessage(content, type) {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}`;
            
            const icon = type === 'bot' ? '🤖' : '👤';
            
            messageDiv.innerHTML = `
                <div class="message-icon">${icon}</div>
                <div class="message-content">${escapeHtml(content)}</div>
            `;
            
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }

        // 显示输入中
        function showTyping() {
            typingIndicator.classList.add('active');
        }

        // 隐藏输入中
        function hideTyping() {
            typingIndicator.classList.remove('active');
        }

        // HTML转义
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML.replace(/\n/g, '<br>');
        }

        // 发送按钮点击
        sendButton.addEventListener('click', sendMessage);

        // 回车发送
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                sendMessage();
            }
        });

        // 页面加载完成，聚焦输入框
        window.addEventListener('load', () => {
            messageInput.focus();
        });
    </script>
</body>
</html>
```

## 部署方案

### 5.1 Docker容器化

#### 5.1.1 Dockerfile

dockerfile

```dockerfile
# Dockerfile
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    default-libmysqlclient-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY pyproject.toml uv.lock ./

# 安装uv
RUN pip install uv

# 安装Python依赖
RUN uv pip install --system -r pyproject.toml

# 复制项目文件
COPY . .

# 暴露端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 5.1.2 docker-compose.yml

```yaml
version: '3.8'

services:
  # MySQL数据库
  mysql:
    image: mysql:8.0
    container_name: telecom_mysql
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME}
    ports:
      - "3306:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./database/schema.sql:/docker-entrypoint-initdb.d/1-schema.sql
      - ./database/init_data.sql:/docker-entrypoint-initdb.d/2-init_data.sql
    networks:
      - telecom_network

  # Redis缓存
  redis:
    image: redis:7-alpine
    container_name: telecom_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - telecom_network

  # Web应用
  web:
    build: .
    container_name: telecom_web
    ports:
      - "8000:8000"
    environment:
      - DB_HOST=mysql
      - DB_PORT=3306
      - DB_USER=${DB_USER}
      - DB_PASSWORD=${DB_PASSWORD}
      - DB_NAME=${DB_NAME}
      - REDIS_HOST=redis
      - REDIS_PORT=6379
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
    depends_on:
      - mysql
      - redis
    networks:
      - telecom_network
    restart: unless-stopped

volumes:
  mysql_data:
  redis_data:

networks:
  telecom_network:
    driver: bridge
```

#### 5.1.3 启动脚本

```bash
#!/bin/bash
# start.sh

echo "启动电信套餐AI客服系统..."

# 加载环境变量
export $(cat .env | xargs)

# 启动Docker Compose
docker-compose up -d

echo "系统启动成功！"
echo "访问地址: http://localhost:8000"
```

## 测试方案

### 6.1 API测试

#### 6.1.1 单元测试

```python
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
```

#### 6.1.2 WebSocket测试

python

```python
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
```

## 使用指南

### 7.1 快速开始

> python -m uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload

#### 7.1.1 本地开发

bash

```bash
# 1. 安装依赖
uv sync

# 2. 配置环境变量
cp .env.example .env
# 编辑.env文件，填写必要的配置

# 3. 启动数据库（Docker）
docker-compose up -d mysql redis

# 4. 运行应用
python -m api.main

# 5. 访问应用
open http://localhost:8000
```

#### 7.1.2 Docker部署

bash

```bash
# 1. 构建镜像
docker-compose build

# 2. 启动所有服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f web

# 4. 停止服务
docker-compose down
```

### 7.2 API使用示例

#### 7.2.1 cURL示例

bash

```bash
# 发送聊天消息
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "有100元以内的套餐吗"
  }'

# 获取会话状态
curl http://localhost:8000/api/session/{session_id}

# 重置会话
curl -X DELETE http://localhost:8000/api/session/{session_id}
```

#### 7.2.2 Python客户端示例

python

```python
# client_example.py
import requests

# 聊天
def chat(message, session_id=None):
    response = requests.post(
        "http://localhost:8000/api/chat",
        json={
            "message": message,
            "session_id": session_id
        }
    )
    return response.json()

# 使用示例
result = chat("有什么套餐")
print(result["response"])

# 继续对话
result2 = chat(
    "100元以内的",
    session_id=result["session_id"]
)
print(result2["response"])
```

## 项目目录结构（完整）

```
telecom-customer-service/
│
├── api/                          # 🆕 Web应用
│   ├── __init__.py
│   ├── main.py                  # FastAPI入口
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── chat.py              # 聊天路由
│   │   └── websocket.py         # WebSocket路由
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── logging.py           # 日志中间件
│   ├── monitoring/
│   │   └── metrics.py           # 监控指标
│   └── static/
│       └── index.html           # 前端页面
│
├── config/                       # 配置
├── core/                        # 核心模块（已有）
├── executor/                    # 执行器（已有）
├── database/                    # 数据库（已有）
├── utils/                       # 工具（已有）
├── tests/                       # 测试
│   ├── test_api.py             # 🆕 API测试
│   └── test_websocket.py       # 🆕 WebSocket测试
│
├── Dockerfile                   # 🆕 Docker配置
├── docker-compose.yml          # 🆕 Docker Compose
├── start.sh                    # 🆕 启动脚本
├── .env                        # 环境变量
├── pyproject.toml              # 项目依赖
└── README.md                   # 项目文档
```

------

## 总结

### 第四阶段成果

✅ **核心功能**

- FastAPI Web服务：RESTful API + WebSocket实时通信
- 简洁前端界面：单文件HTML聊天界面
- Docker容器化：一键部署方案
- 完善的监控和日志系统

✅ **技术特点**

- 🚀 高性能异步架构
- 💬 实时双向通信
- 📦 容器化部署
- 📊 可观测性（日志+监控）

✅ **部署方式**

- 本地开发：直接运行
- Docker部署：docker-compose一键启动
- 生产环境：Nginx + Systemd