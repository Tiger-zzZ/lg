from fastapi import APIRouter
from .auth import router as auth_router
from .agents import router as agents_router
from .documents import router as documents_router

# 创建主路由
api_router = APIRouter()

# 包含所有子路由
api_router.include_router(auth_router)
api_router.include_router(agents_router)
api_router.include_router(documents_router)


@api_router.get("/")
async def api_root():
    """API根端点"""
    return {
        "message": "LG Platform API v1",
        "endpoints": {
            "docs": "/docs",
            "health": "/health",
            "metrics": "/metrics",
            "auth": "/api/v1/auth",
            "agents": "/api/v1/agents",
            "documents": "/api/v1/documents",
        }
    }

@api_router.get("/chat")
async def chat_sessions():
    """聊天会话 (占位符)"""
    return {"sessions": [], "message": "聊天功能即将实现"}