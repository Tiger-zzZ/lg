from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
import asyncio

from ..agents.manager import agent_manager
from ..schemas.agent import (
    AgentCreateRequest,
    AgentExecuteRequest,
    AgentResponse,
    AgentExecutionResponse
)
from .auth import get_current_user
from ..models.user import User
from ..core.logging import logger

# 创建路由
router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/types", response_model=Dict[str, str])
async def get_agent_types():
    """获取可用的Agent类型"""
    return agent_manager.get_available_types()


@router.post("/create", response_model=AgentResponse)
async def create_agent(
    request: AgentCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """创建新的Agent"""
    try:
        agent = agent_manager.create_agent(request.type)

        # 如果提供了自定义名称，更新Agent名称
        if request.name:
            agent.name = request.name

        logger.info(
            "Agent created",
            agent_id=agent.id,
            agent_type=request.type,
            user_id=str(current_user.id)
        )

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            type=request.type,
            created_at=agent.created_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[AgentResponse])
async def list_agents(current_user: User = Depends(get_current_user)):
    """列出所有Agent"""
    agents = agent_manager.list_agents()

    return [
        AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            type="unknown",  # TODO: 添加类型追踪
            created_at=agent.created_at,
        )
        for agent in agents.values()
    ]


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """获取特定Agent信息"""
    try:
        agent = agent_manager.get_agent(agent_id)

        return AgentResponse(
            id=agent.id,
            name=agent.name,
            description=agent.description,
            type="unknown",  # TODO: 添加类型追踪
            created_at=agent.created_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_id: str,
    request: AgentExecuteRequest,
    current_user: User = Depends(get_current_user)
):
    """执行Agent"""
    try:
        agent = agent_manager.get_agent(agent_id)

        logger.info(
            "Agent execution started",
            agent_id=agent_id,
            user_id=str(current_user.id),
            message_count=len(request.messages)
        )

        # 执行Agent
        result = await agent.execute(request.messages, request.metadata)

        logger.info(
            "Agent execution completed",
            agent_id=agent_id,
            execution_id=result["execution_id"],
            status=result["status"],
            duration=result["metadata"].get("duration")
        )

        return AgentExecutionResponse(
            execution_id=result["execution_id"],
            agent_id=agent_id,
            agent_name=agent.name,
            status=result["status"],
            result=result["result"],
            metadata=result["metadata"],
            duration=result["metadata"].get("duration")
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "Agent execution failed",
            agent_id=agent_id,
            user_id=str(current_user.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user)
):
    """删除Agent"""
    success = agent_manager.remove_agent(agent_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    logger.info(
        "Agent deleted",
        agent_id=agent_id,
        user_id=str(current_user.id)
    )

    return {"message": "Agent deleted successfully"}