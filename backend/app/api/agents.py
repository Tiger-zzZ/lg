from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict
import asyncio
from datetime import datetime

from app.agents.manager import agent_manager
from app.api.schemas.agent import (
    AgentCreateRequest,
    AgentExecuteRequest,
    AgentResponse,
    AgentExecutionResponse,
    AgentConfigRequest,
    AgentExecutionHistoryResponse
)
from app.api.auth import get_current_user
from app.models.user import User
from app.models.agent import Agent, AgentExecution
from app.core.database import get_db
from app.core.logging import logger

# 创建路由
router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/types", response_model=Dict[str, str])
async def get_agent_types():
    """获取可用的Agent类型"""
    return agent_manager.get_available_types()


# 临时测试端点 - 无需认证
@router.post("/test/create", response_model=AgentResponse)
async def create_agent_test(request: AgentCreateRequest, db: Session = Depends(get_db)):
    """创建新的Agent (测试用，无需认证)"""
    try:
        # 创建内存中的agent实例
        agent_instance = agent_manager.create_agent(request.type)

        # 创建数据库记录
        db_agent = Agent(
            name=request.name or agent_instance.name,
            description=request.description or agent_instance.description,
            type=request.type,
            config=request.config or {},
            user_id="00000000-0000-0000-0000-000000000000"  # 测试用默认用户ID
        )

        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)

        logger.info(
            "Agent created (test)",
            agent_id=str(db_agent.id),
            agent_type=request.type,
        )

        return AgentResponse(
            id=str(db_agent.id),
            name=db_agent.name,
            description=db_agent.description,
            type=db_agent.type,
            config=db_agent.config,
            is_active=db_agent.is_active,
            status=db_agent.status,
            created_at=db_agent.created_at,
            updated_at=db_agent.updated_at,
            last_used_at=db_agent.last_used_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/test/execute/{agent_id}", response_model=AgentExecutionResponse)
async def execute_agent_test(
    agent_id: str,
    request: AgentExecuteRequest,
    db: Session = Depends(get_db)
):
    """执行Agent (测试用，无需认证)"""
    # 查找数据库中的agent
    db_agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not db_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if not db_agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active"
        )

    try:
        # 创建执行记录
        execution = AgentExecution(
            agent_id=db_agent.id,
            user_id=db_agent.user_id,  # 使用agent的所有者ID
            input_data={
                "messages": request.messages,
                "metadata": request.metadata
            },
            status="running"
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # 更新agent状态和最后使用时间
        db_agent.status = "running"
        db_agent.last_used_at = datetime.utcnow()
        db.commit()

        logger.info(
            "Agent execution started (test)",
            agent_id=agent_id,
            execution_id=str(execution.id),
            message_count=len(request.messages)
        )

        # 创建运行时agent实例并执行
        agent_instance = agent_manager.create_agent(db_agent.type)
        result = await agent_instance.execute(request.messages, request.metadata)

        # 更新执行记录
        execution.output_data = {
            "result": result["result"],
            "metadata": result["metadata"]
        }
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        execution.duration_ms = str(result["metadata"].get("duration", 0))

        # 更新agent状态
        db_agent.status = "idle"
        db.commit()

        logger.info(
            "Agent execution completed (test)",
            agent_id=agent_id,
            execution_id=str(execution.id),
            status=result["status"],
            duration=result["metadata"].get("duration")
        )

        return AgentExecutionResponse(
            execution_id=str(execution.id),
            agent_id=agent_id,
            agent_name=db_agent.name,
            status=result["status"],
            result=result["result"],
            metadata=result["metadata"],
            duration=result["metadata"].get("duration")
        )

    except Exception as e:
        # 更新执行记录为失败状态
        execution.status = "failed"
        execution.error_message = str(e)
        execution.completed_at = datetime.utcnow()

        # 重置agent状态
        db_agent.status = "error"
        db.commit()

        logger.error(
            "Agent execution failed (test)",
            agent_id=agent_id,
            execution_id=str(execution.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.get("/test/list", response_model=List[AgentResponse])
async def list_agents_test(db: Session = Depends(get_db)):
    """列出所有Agent (测试用，无需认证)"""
    agents = db.query(Agent).all()

    return [
        AgentResponse(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            type=agent.type,
            config=agent.config,
            is_active=agent.is_active,
            status=agent.status,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            last_used_at=agent.last_used_at,
        )
        for agent in agents
    ]


@router.put("/test/toggle/{agent_id}", response_model=AgentResponse)
async def toggle_agent_status_test(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """切换Agent启用/禁用状态 (测试用，无需认证)"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    agent.is_active = not agent.is_active
    agent.status = "idle" if agent.is_active else "disabled"
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    logger.info(
        "Agent status toggled (test)",
        agent_id=agent_id,
        is_active=agent.is_active
    )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        type=agent.type,
        config=agent.config,
        is_active=agent.is_active,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        last_used_at=agent.last_used_at,
    )


@router.delete("/test/delete/{agent_id}")
async def delete_agent_test(
    agent_id: str,
    db: Session = Depends(get_db)
):
    """删除Agent (测试用，无需认证)"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    db.delete(agent)
    db.commit()

    # 从内存中移除（如果存在）
    agent_manager.remove_agent(agent_id)

    logger.info(
        "Agent deleted (test)",
        agent_id=agent_id
    )

    return {"message": "Agent deleted successfully"}


@router.put("/test/config/{agent_id}", response_model=AgentResponse)
async def update_agent_config_test(
    agent_id: str,
    request: AgentConfigRequest,
    db: Session = Depends(get_db)
):
    """更新Agent配置 (测试用，无需认证)"""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    agent.config = request.config
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    logger.info(
        "Agent config updated (test)",
        agent_id=agent_id
    )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        type=agent.type,
        config=agent.config,
        is_active=agent.is_active,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        last_used_at=agent.last_used_at,
    )


@router.get("/test/executions/{agent_id}", response_model=List[AgentExecutionHistoryResponse])
async def get_agent_executions_test(
    agent_id: str,
    db: Session = Depends(get_db),
    limit: int = 20
):
    """获取Agent执行历史 (测试用，无需认证)"""
    # 验证agent存在
    agent = db.query(Agent).filter(Agent.id == agent_id).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    executions = db.query(AgentExecution).filter(
        AgentExecution.agent_id == agent_id
    ).order_by(AgentExecution.started_at.desc()).limit(limit).all()

    return [
        AgentExecutionHistoryResponse(
            id=str(execution.id),
            agent_id=str(execution.agent_id),
            input_data=execution.input_data,
            output_data=execution.output_data,
            status=execution.status,
            error_message=execution.error_message,
            duration_ms=execution.duration_ms,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )
        for execution in executions
    ]


@router.post("/create", response_model=AgentResponse)
async def create_agent(
    request: AgentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建新的Agent"""
    try:
        # 创建内存中的agent实例
        agent_instance = agent_manager.create_agent(request.type)

        # 创建数据库记录
        db_agent = Agent(
            name=request.name or agent_instance.name,
            description=request.description or agent_instance.description,
            type=request.type,
            config=request.config or {},
            user_id=current_user.id
        )

        db.add(db_agent)
        db.commit()
        db.refresh(db_agent)

        logger.info(
            "Agent created",
            agent_id=str(db_agent.id),
            agent_type=request.type,
            user_id=str(current_user.id)
        )

        return AgentResponse(
            id=str(db_agent.id),
            name=db_agent.name,
            description=db_agent.description,
            type=db_agent.type,
            config=db_agent.config,
            is_active=db_agent.is_active,
            status=db_agent.status,
            created_at=db_agent.created_at,
            updated_at=db_agent.updated_at,
            last_used_at=db_agent.last_used_at,
        )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/", response_model=List[AgentResponse])
async def list_agents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """列出当前用户的所有Agent（包含统计信息）"""
    agents = db.query(Agent).filter(Agent.user_id == current_user.id).all()

    result = []
    for agent in agents:
        # 查询执行统计
        executions = db.query(AgentExecution).filter(
            AgentExecution.agent_id == agent.id
        ).all()

        execution_count = len(executions)
        completed_executions = [e for e in executions if e.status == 'completed']
        success_count = len(completed_executions)
        success_rate = (success_count / execution_count * 100) if execution_count > 0 else 0

        # 计算平均执行时长（确保类型转换）
        durations = []
        for e in completed_executions:
            if e.duration_ms is not None:
                # 确保转换为float类型
                try:
                    duration = float(e.duration_ms)
                    durations.append(duration)
                except (TypeError, ValueError):
                    continue
        avg_duration = sum(durations) / len(durations) if durations else None

        # 获取最后一次执行
        last_execution = db.query(AgentExecution).filter(
            AgentExecution.agent_id == agent.id
        ).order_by(AgentExecution.started_at.desc()).first()

        agent_response = AgentResponse(
            id=str(agent.id),
            name=agent.name,
            description=agent.description,
            type=agent.type,
            config=agent.config,
            is_active=agent.is_active,
            status=agent.status,
            created_at=agent.created_at,
            updated_at=agent.updated_at,
            last_used_at=agent.last_used_at,
        )

        # 添加统计字段（使用额外字段）
        agent_dict = agent_response.dict()
        agent_dict['execution_count'] = execution_count
        agent_dict['success_rate'] = round(success_rate, 1)
        agent_dict['avg_duration'] = round(avg_duration) if avg_duration else None
        agent_dict['last_execution'] = {
            'id': str(last_execution.id),
            'status': last_execution.status,
            'started_at': last_execution.started_at.isoformat() if last_execution.started_at else None,
            'error_message': last_execution.error_message
        } if last_execution else None

        result.append(agent_dict)

    return result


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取特定Agent信息"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        type=agent.type,
        config=agent.config,
        is_active=agent.is_active,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        last_used_at=agent.last_used_at,
    )


@router.post("/{agent_id}/execute", response_model=AgentExecutionResponse)
async def execute_agent(
    agent_id: str,
    request: AgentExecuteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """执行Agent"""
    # 查找数据库中的agent
    db_agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not db_agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    if not db_agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is not active"
        )

    try:
        # 创建执行记录
        execution = AgentExecution(
            agent_id=db_agent.id,
            user_id=current_user.id,
            input_data={
                "messages": request.messages,
                "metadata": request.metadata
            },
            status="running"
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # 更新agent状态和最后使用时间
        db_agent.status = "running"
        db_agent.last_used_at = datetime.utcnow()
        db.commit()

        logger.info(
            "Agent execution started",
            agent_id=agent_id,
            execution_id=str(execution.id),
            user_id=str(current_user.id),
            message_count=len(request.messages)
        )

        # 创建运行时agent实例并执行
        agent_instance = agent_manager.create_agent(db_agent.type)
        result = await agent_instance.execute(request.messages, request.metadata)

        # 更新执行记录
        execution.output_data = {
            "result": result["result"],
            "metadata": result["metadata"]
        }
        execution.status = "completed"
        execution.completed_at = datetime.utcnow()
        execution.duration_ms = str(result["metadata"].get("duration", 0))

        # 更新agent状态
        db_agent.status = "idle"
        db.commit()

        logger.info(
            "Agent execution completed",
            agent_id=agent_id,
            execution_id=str(execution.id),
            status=result["status"],
            duration=result["metadata"].get("duration")
        )

        return AgentExecutionResponse(
            execution_id=str(execution.id),
            agent_id=agent_id,
            agent_name=db_agent.name,
            status=result["status"],
            result=result["result"],
            metadata=result["metadata"],
            duration=result["metadata"].get("duration")
        )

    except Exception as e:
        # 更新执行记录为失败状态
        execution.status = "failed"
        execution.error_message = str(e)
        execution.completed_at = datetime.utcnow()

        # 重置agent状态
        db_agent.status = "error"
        db.commit()

        logger.error(
            "Agent execution failed",
            agent_id=agent_id,
            execution_id=str(execution.id),
            user_id=str(current_user.id),
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Agent execution failed: {str(e)}"
        )


@router.put("/{agent_id}/config", response_model=AgentResponse)
async def update_agent_config(
    agent_id: str,
    request: AgentConfigRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新Agent配置"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    agent.config = request.config
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    logger.info(
        "Agent config updated",
        agent_id=agent_id,
        user_id=str(current_user.id)
    )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        type=agent.type,
        config=agent.config,
        is_active=agent.is_active,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        last_used_at=agent.last_used_at,
    )


@router.get("/{agent_id}/executions", response_model=List[AgentExecutionHistoryResponse])
async def get_agent_executions(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 20
):
    """获取Agent执行历史"""
    # 验证agent归属
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    executions = db.query(AgentExecution).filter(
        AgentExecution.agent_id == agent_id
    ).order_by(AgentExecution.started_at.desc()).limit(limit).all()

    return [
        AgentExecutionHistoryResponse(
            id=str(execution.id),
            agent_id=str(execution.agent_id),
            input_data=execution.input_data,
            output_data=execution.output_data,
            status=execution.status,
            error_message=execution.error_message,
            duration_ms=execution.duration_ms,
            started_at=execution.started_at,
            completed_at=execution.completed_at,
        )
        for execution in executions
    ]


@router.put("/{agent_id}/toggle", response_model=AgentResponse)
async def toggle_agent_status(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """切换Agent启用/禁用状态"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    agent.is_active = not agent.is_active
    agent.status = "idle" if agent.is_active else "disabled"
    agent.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(agent)

    logger.info(
        "Agent status toggled",
        agent_id=agent_id,
        is_active=agent.is_active,
        user_id=str(current_user.id)
    )

    return AgentResponse(
        id=str(agent.id),
        name=agent.name,
        description=agent.description,
        type=agent.type,
        config=agent.config,
        is_active=agent.is_active,
        status=agent.status,
        created_at=agent.created_at,
        updated_at=agent.updated_at,
        last_used_at=agent.last_used_at,
    )


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除Agent"""
    agent = db.query(Agent).filter(
        Agent.id == agent_id,
        Agent.user_id == current_user.id
    ).first()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found"
        )

    db.delete(agent)
    db.commit()

    # 从内存中移除（如果存在）
    agent_manager.remove_agent(agent_id)

    logger.info(
        "Agent deleted",
        agent_id=agent_id,
        user_id=str(current_user.id)
    )

    return {"message": "Agent deleted successfully"}