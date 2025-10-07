from contextlib import asynccontextmanager
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from api.routers import chat, websocket
from utils import logger

# 应用状态管理
app_state = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动逻辑
    logger.info("🚀 FastAPI应用启动中...")

    # 这里可以添加更多启动初始化代码
    # 例如：数据库连接、缓存初始化、模型加载等
    app_state["started"] = True
    app_state["startup_time"] = "你的启动时间"

    logger.info("✅ FastAPI应用启动成功")

    yield  # 应用运行期间

    # 关闭逻辑
    logger.info("🛑 FastAPI应用关闭中...")

    # 这里可以添加清理代码
    # 例如：关闭数据库连接、清理资源等
    app_state.clear()

    logger.info("✅ FastAPI应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="电信套餐AI客服系统",
    description="智能对话API",
    version="1.0.0",
    lifespan=lifespan
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


# 可选：添加一个健康检查端点来查看应用状态
@app.get("/health")
async def health_check():
    return {
        "status": "running",
        "started": app_state.get("started", False)
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )