"""
Agent协作API
提供多Agent协作的管理接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.collaboration import collaboration_manager, CollaborationRole, MessageType
from app.agents.collaboration.agents import (
    CoordinatorAgent, DataAnalysisSpecialist, ReviewerAgent, MonitorAgent
)
from app.api.auth import get_current_user
from app.models.user import User
from app.core.logging import logger

router = APIRouter()


class AgentCreateRequest(BaseModel):
    """Agent创建请求"""
    agent_type: str  # coordinator, data_specialist, reviewer, monitor
    name: Optional[str] = None
    specialties: List[str] = []


class TaskAssignRequest(BaseModel):
    """任务分配请求"""
    task_name: str
    task_description: str
    assigned_to: str
    assigned_by: str = "system"
    priority: int = 1
    parameters: Dict[str, Any] = {}


class CollaborationSessionRequest(BaseModel):
    """协作会话创建请求"""
    session_name: str
    participant_agents: List[str]
    coordinator_agent: Optional[str] = None


class MessageSendRequest(BaseModel):
    """消息发送请求"""
    from_agent: str
    to_agent: str
    message_type: str
    content: Any
    requires_response: bool = False


class WorkflowExecuteRequest(BaseModel):
    """协作工作流执行请求"""
    workflow_name: str
    tasks: List[Dict[str, Any]]


# 全局Agent实例管理
collaborative_agents: Dict[str, Any] = {}


@router.post("/collaboration/agents")
async def create_collaborative_agent(
    request: AgentCreateRequest,
    current_user: User = Depends(get_current_user)
):
    """创建协作Agent"""
    try:
        agent_type = request.agent_type.lower()

        if agent_type == "coordinator":
            agent = CoordinatorAgent()
        elif agent_type == "data_specialist":
            agent = DataAnalysisSpecialist()
        elif agent_type == "reviewer":
            agent = ReviewerAgent()
        elif agent_type == "monitor":
            agent = MonitorAgent()
        else:
            raise HTTPException(status_code=400, detail=f"不支持的Agent类型: {request.agent_type}")

        # 自定义名称
        if request.name:
            agent.name = request.name

        # 添加特长
        if request.specialties:
            agent.specialties.extend(request.specialties)

        # 注册到协作系统
        collaboration_manager.register_agent(agent)
        collaborative_agents[agent.id] = agent

        logger.info(f"创建协作Agent: {agent.name} (类型: {agent_type})")

        return {
            "agent_id": agent.id,
            "name": agent.name,
            "description": agent.description,
            "role": agent.collaboration_role.value,
            "specialties": agent.specialties,
            "type": agent_type
        }

    except Exception as e:
        logger.error(f"创建协作Agent失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建Agent失败: {str(e)}")


@router.get("/collaboration/agents")
async def list_collaborative_agents(current_user: User = Depends(get_current_user)):
    """列出所有协作Agent"""
    try:
        agents_info = []
        for agent_id, agent in collaboration_manager.agents.items():
            agents_info.append({
                "agent_id": agent_id,
                "name": agent.name,
                "description": agent.description,
                "role": getattr(agent, 'collaboration_role', 'unknown').value if hasattr(getattr(agent, 'collaboration_role', None), 'value') else 'unknown',
                "specialties": getattr(agent, 'specialties', []),
                "assigned_tasks": len(getattr(agent, 'assigned_tasks', []))
            })

        return {
            "agents": agents_info,
            "total_count": len(agents_info),
            "stats": collaboration_manager.get_collaboration_stats()
        }

    except Exception as e:
        logger.error(f"列出协作Agent失败: {e}")
        raise HTTPException(status_code=500, detail="获取Agent列表失败")


@router.post("/collaboration/tasks/assign")
async def assign_task(
    request: TaskAssignRequest,
    current_user: User = Depends(get_current_user)
):
    """分配任务"""
    try:
        # 验证Agent存在
        if request.assigned_to not in collaboration_manager.agents:
            raise HTTPException(status_code=404, detail=f"目标Agent不存在: {request.assigned_to}")

        if request.assigned_by != "system" and request.assigned_by not in collaboration_manager.agents:
            raise HTTPException(status_code=404, detail=f"分配者Agent不存在: {request.assigned_by}")

        # 分配任务
        message_id = await collaboration_manager.assign_task(
            task_name=request.task_name,
            task_description=request.task_description,
            assigned_to=request.assigned_to,
            assigned_by=request.assigned_by,
            parameters=request.parameters
        )

        return {
            "message_id": message_id,
            "task_name": request.task_name,
            "assigned_to": request.assigned_to,
            "assigned_by": request.assigned_by,
            "status": "assigned"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"任务分配失败: {e}")
        raise HTTPException(status_code=500, detail=f"任务分配失败: {str(e)}")


@router.post("/collaboration/sessions")
async def create_collaboration_session(
    request: CollaborationSessionRequest,
    current_user: User = Depends(get_current_user)
):
    """创建协作会话"""
    try:
        # 验证参与者Agent存在
        for agent_id in request.participant_agents:
            if agent_id not in collaboration_manager.agents:
                raise HTTPException(status_code=404, detail=f"参与者Agent不存在: {agent_id}")

        # 创建协作会话
        session_id = await collaboration_manager.create_collaboration_session(
            session_name=request.session_name,
            participant_agents=request.participant_agents,
            coordinator_agent=request.coordinator_agent
        )

        return {
            "session_id": session_id,
            "session_name": request.session_name,
            "participants": request.participant_agents,
            "coordinator": request.coordinator_agent or request.participant_agents[0],
            "status": "created"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建协作会话失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建会话失败: {str(e)}")


@router.post("/collaboration/messages/send")
async def send_message(
    request: MessageSendRequest,
    current_user: User = Depends(get_current_user)
):
    """发送消息"""
    try:
        # 验证消息类型
        try:
            message_type = MessageType(request.message_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"无效的消息类型: {request.message_type}")

        # 验证Agent存在
        if request.from_agent != "system" and request.from_agent not in collaboration_manager.agents:
            raise HTTPException(status_code=404, detail=f"发送者Agent不存在: {request.from_agent}")

        if request.to_agent != "system" and request.to_agent not in collaboration_manager.agents:
            raise HTTPException(status_code=404, detail=f"接收者Agent不存在: {request.to_agent}")

        # 发送消息
        from app.agents.collaboration import AgentMessage

        message = AgentMessage(
            from_agent=request.from_agent,
            to_agent=request.to_agent,
            message_type=message_type,
            content=request.content,
            requires_response=request.requires_response
        )

        success = await collaboration_manager.send_message(message)

        return {
            "message_id": message.id,
            "success": success,
            "from_agent": request.from_agent,
            "to_agent": request.to_agent,
            "message_type": request.message_type,
            "timestamp": message.timestamp.isoformat()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"发送消息失败: {e}")
        raise HTTPException(status_code=500, detail=f"发送消息失败: {str(e)}")


@router.post("/collaboration/workflows/execute")
async def execute_collaborative_workflow(
    request: WorkflowExecuteRequest,
    current_user: User = Depends(get_current_user)
):
    """执行协作工作流"""
    try:
        # 验证任务中的Agent存在
        for task in request.tasks:
            agent_id = task.get("agent_id")
            if not agent_id:
                raise HTTPException(status_code=400, detail="任务缺少agent_id字段")

            if agent_id not in collaboration_manager.agents:
                raise HTTPException(status_code=404, detail=f"任务中的Agent不存在: {agent_id}")

        # 执行协作工作流
        result = await collaboration_manager.execute_collaborative_workflow({
            "name": request.workflow_name,
            "tasks": request.tasks
        })

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行协作工作流失败: {e}")
        raise HTTPException(status_code=500, detail=f"工作流执行失败: {str(e)}")


@router.get("/collaboration/stats")
async def get_collaboration_stats(current_user: User = Depends(get_current_user)):
    """获取协作统计信息"""
    try:
        stats = collaboration_manager.get_collaboration_stats()
        return stats

    except Exception as e:
        logger.error(f"获取协作统计失败: {e}")
        raise HTTPException(status_code=500, detail="获取统计信息失败")


@router.get("/collaboration/sessions")
async def list_collaboration_sessions(current_user: User = Depends(get_current_user)):
    """列出协作会话"""
    try:
        sessions = []
        for session_id, session in collaboration_manager.collaboration_sessions.items():
            sessions.append({
                "session_id": session_id,
                "name": session["name"],
                "participants": session["participants"],
                "coordinator": session["coordinator"],
                "status": session["status"],
                "created_at": session["created_at"].isoformat(),
                "message_count": len(session["messages"])
            })

        return {
            "sessions": sessions,
            "total_count": len(sessions)
        }

    except Exception as e:
        logger.error(f"列出协作会话失败: {e}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")


@router.get("/collaboration/messages")
async def list_messages(
    limit: int = 50,
    message_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """列出消息"""
    try:
        messages = collaboration_manager.message_queue

        # 过滤消息类型
        if message_type:
            try:
                filter_type = MessageType(message_type)
                messages = [m for m in messages if m.message_type == filter_type]
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的消息类型: {message_type}")

        # 按时间排序并限制数量
        messages = sorted(messages, key=lambda x: x.timestamp, reverse=True)[:limit]

        message_list = []
        for message in messages:
            message_list.append({
                "message_id": message.id,
                "from_agent": message.from_agent,
                "to_agent": message.to_agent,
                "message_type": message.message_type.value,
                "content": message.content,
                "timestamp": message.timestamp.isoformat(),
                "requires_response": message.requires_response
            })

        return {
            "messages": message_list,
            "total_count": len(message_list)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"列出消息失败: {e}")
        raise HTTPException(status_code=500, detail="获取消息列表失败")


@router.get("/collaboration/tasks")
async def list_tasks(current_user: User = Depends(get_current_user)):
    """列出任务分配"""
    try:
        tasks = []
        for task_id, task in collaboration_manager.task_assignments.items():
            tasks.append({
                "task_id": task_id,
                "task_name": task.task_name,
                "task_description": task.task_description,
                "assigned_to": task.assigned_to,
                "assigned_by": task.assigned_by,
                "priority": task.priority,
                "status": task.status,
                "created_at": task.created_at.isoformat(),
                "has_result": task.result is not None
            })

        return {
            "tasks": tasks,
            "total_count": len(tasks)
        }

    except Exception as e:
        logger.error(f"列出任务失败: {e}")
        raise HTTPException(status_code=500, detail="获取任务列表失败")