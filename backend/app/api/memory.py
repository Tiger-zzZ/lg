"""
Agent记忆API路由
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.memory import AgentMemory, MemoryType, MemoryImportance
from app.api.auth import get_current_user
from app.models.user import User
from app.core.logging import logger

router = APIRouter()


class MemoryCreate(BaseModel):
    """创建记忆请求"""
    agent_id: str
    content: str
    memory_type: str = "short_term"
    importance: int = 2
    tags: List[str] = []
    metadata: Dict[str, Any] = {}
    ttl_hours: Optional[int] = None


class MemoryResponse(BaseModel):
    """记忆响应"""
    id: str
    agent_id: str
    content: str
    memory_type: str
    importance: int
    tags: List[str]
    metadata: Dict[str, Any]
    created_at: str
    last_accessed: str
    access_count: int


class MemorySearch(BaseModel):
    """记忆搜索请求"""
    agent_id: str
    query: str
    memory_type: Optional[str] = None
    limit: int = 10


@router.post("/memories", response_model=Dict[str, str])
async def create_memory(
    request: MemoryCreate,
    current_user: User = Depends(get_current_user)
):
    """创建新记忆"""
    try:
        # 验证记忆类型
        try:
            memory_type = MemoryType(request.memory_type)
            importance = MemoryImportance(request.importance)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"无效的参数: {e}")

        # 创建记忆管理器
        memory_manager = AgentMemory(request.agent_id)

        # 存储记忆
        memory_id = await memory_manager.remember(
            content=request.content,
            memory_type=memory_type,
            importance=importance,
            tags=request.tags,
            metadata=request.metadata,
            ttl_hours=request.ttl_hours
        )

        return {"memory_id": memory_id, "status": "success"}

    except Exception as e:
        logger.error(f"创建记忆失败: {e}")
        raise HTTPException(status_code=500, detail="创建记忆失败")


@router.post("/memories/search", response_model=List[MemoryResponse])
async def search_memories(
    request: MemorySearch,
    current_user: User = Depends(get_current_user)
):
    """搜索记忆"""
    try:
        # 创建记忆管理器
        memory_manager = AgentMemory(request.agent_id)

        # 解析记忆类型
        memory_type = None
        if request.memory_type:
            try:
                memory_type = MemoryType(request.memory_type)
            except ValueError:
                raise HTTPException(status_code=400, detail="无效的记忆类型")

        # 搜索记忆
        memories = await memory_manager.recall(
            query=request.query,
            memory_type=memory_type,
            limit=request.limit
        )

        # 转换为响应格式
        return [
            MemoryResponse(
                id=memory.id,
                agent_id=memory.agent_id,
                content=memory.content,
                memory_type=memory.memory_type.value,
                importance=memory.importance.value,
                tags=memory.tags,
                metadata=memory.metadata,
                created_at=memory.created_at.isoformat(),
                last_accessed=memory.last_accessed.isoformat(),
                access_count=memory.access_count
            )
            for memory in memories
        ]

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"搜索记忆失败: {e}")
        raise HTTPException(status_code=500, detail="搜索记忆失败")


@router.delete("/memories/{memory_id}")
async def delete_memory(
    memory_id: str,
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除记忆"""
    try:
        # 创建记忆管理器
        memory_manager = AgentMemory(agent_id)

        # 删除记忆
        success = await memory_manager.forget(memory_id)

        if success:
            return {"status": "success", "message": "记忆已删除"}
        else:
            raise HTTPException(status_code=404, detail="记忆不存在或删除失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除记忆失败: {e}")
        raise HTTPException(status_code=500, detail="删除记忆失败")


@router.get("/memories/{agent_id}/summary")
async def get_memory_summary(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取Agent记忆摘要"""
    try:
        # 创建记忆管理器
        memory_manager = AgentMemory(agent_id)

        # 获取摘要
        summary = await memory_manager.get_memory_summary()

        return summary

    except Exception as e:
        logger.error(f"获取记忆摘要失败: {e}")
        raise HTTPException(status_code=500, detail="获取记忆摘要失败")


@router.get("/memories/types")
async def get_memory_types(current_user: User = Depends(get_current_user)):
    """获取可用的记忆类型"""
    return {
        "memory_types": [
            {"value": t.value, "name": t.value.replace("_", " ").title()}
            for t in MemoryType
        ],
        "importance_levels": [
            {"value": i.value, "name": f"Level {i.value}"}
            for i in MemoryImportance
        ]
    }
