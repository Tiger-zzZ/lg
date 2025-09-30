from fastapi import APIRouter
from app.api.auth import router as auth_router
from app.api.agents import router as agents_router
from app.api.documents import router as documents_router
from app.api.chat import router as chat_router
from app.api.prompts import router as prompts_router
from app.api.memory import router as memory_router
from app.api.tools import router as tools_router
from app.api.workflows import router as workflows_router
from app.api.collaboration import router as collaboration_router

# 创建主路由
api_router = APIRouter()

# 包含所有子路由
api_router.include_router(auth_router)
api_router.include_router(agents_router)
api_router.include_router(documents_router)
api_router.include_router(chat_router)
api_router.include_router(prompts_router, prefix="/prompts", tags=["prompts"])
api_router.include_router(memory_router, prefix="/memory", tags=["memory"])
api_router.include_router(tools_router, prefix="/tools", tags=["tools"])
api_router.include_router(workflows_router, prefix="/workflows", tags=["workflows"])
api_router.include_router(collaboration_router, prefix="/collaboration", tags=["collaboration"])


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
            "chat": "/api/v1/chat",
            "prompts": "/api/v1/prompts",
            "memory": "/api/v1/memory",
            "tools": "/api/v1/tools",
            "workflows": "/api/v1/workflows",
            "collaboration": "/api/v1/collaboration",
        }
    }

@api_router.get("/chat")
async def chat_sessions():
    """聊天会话 (占位符)"""
    return {"sessions": [], "message": "聊天功能即将实现"}