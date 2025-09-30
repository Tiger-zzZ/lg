"""
多Agent协作模式
支持Agent之间的协调、通信和任务分工
"""

from typing import Dict, Any, List, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum
import uuid
import asyncio
from datetime import datetime
import json

from app.agents.base import BaseAgent, AgentState
from app.agents.workflow import ComplexFlow, FlowNode, FlowNodeType, flow_engine
from app.core.logging import logger


class CollaborationRole(Enum):
    """协作角色"""
    COORDINATOR = "coordinator"    # 协调者
    EXECUTOR = "executor"         # 执行者
    REVIEWER = "reviewer"         # 审查者
    SPECIALIST = "specialist"     # 专家
    MONITOR = "monitor"          # 监控者


class MessageType(Enum):
    """消息类型"""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_COMPLETION = "task_completion"
    REQUEST_HELP = "request_help"
    PROVIDE_FEEDBACK = "provide_feedback"
    STATUS_UPDATE = "status_update"
    ERROR_REPORT = "error_report"
    COLLABORATION_REQUEST = "collaboration_request"


@dataclass
class AgentMessage:
    """Agent间消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    from_agent: str = ""
    to_agent: str = ""
    message_type: MessageType = MessageType.STATUS_UPDATE
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    requires_response: bool = False
    correlation_id: Optional[str] = None  # 关联消息ID


@dataclass
class TaskAssignment:
    """任务分配"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    task_name: str = ""
    task_description: str = ""
    assigned_to: str = ""
    assigned_by: str = ""
    priority: int = 1  # 1-10, 10最高
    deadline: Optional[datetime] = None
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    status: str = "assigned"  # assigned, in_progress, completed, failed
    result: Any = None
    created_at: datetime = field(default_factory=datetime.utcnow)


class AgentCollaboration:
    """Agent协作管理器"""

    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.message_queue: List[AgentMessage] = []
        self.task_assignments: Dict[str, TaskAssignment] = {}
        self.collaboration_sessions: Dict[str, Dict[str, Any]] = {}
        self.message_handlers: Dict[MessageType, Callable] = {}

        self._setup_default_handlers()

    def register_agent(self, agent: BaseAgent, role: CollaborationRole = CollaborationRole.EXECUTOR):
        """注册Agent到协作系统"""
        self.agents[agent.id] = agent

        # 添加协作属性
        agent.collaboration_role = role
        agent.collaboration_manager = self

        logger.info(f"注册Agent到协作系统: {agent.name} (角色: {role.value})")

    def _setup_default_handlers(self):
        """设置默认消息处理器"""
        self.message_handlers = {
            MessageType.TASK_ASSIGNMENT: self._handle_task_assignment,
            MessageType.TASK_COMPLETION: self._handle_task_completion,
            MessageType.REQUEST_HELP: self._handle_request_help,
            MessageType.STATUS_UPDATE: self._handle_status_update,
            MessageType.ERROR_REPORT: self._handle_error_report,
        }

    async def send_message(self, message: AgentMessage) -> bool:
        """发送消息"""
        try:
            # 验证接收者存在
            if message.to_agent not in self.agents:
                logger.error(f"接收者Agent不存在: {message.to_agent}")
                return False

            # 添加到消息队列
            self.message_queue.append(message)

            # 处理消息
            await self._process_message(message)

            logger.debug(f"消息发送成功: {message.from_agent} -> {message.to_agent}")
            return True

        except Exception as e:
            logger.error(f"消息发送失败: {e}")
            return False

    async def _process_message(self, message: AgentMessage):
        """处理消息"""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            await handler(message)
        else:
            logger.warning(f"未知消息类型: {message.message_type}")

    async def _handle_task_assignment(self, message: AgentMessage):
        """处理任务分配消息"""
        try:
            task_data = message.content
            task = TaskAssignment(
                task_name=task_data["task_name"],
                task_description=task_data["task_description"],
                assigned_to=message.to_agent,
                assigned_by=message.from_agent,
                priority=task_data.get("priority", 1),
                parameters=task_data.get("parameters", {})
            )

            self.task_assignments[task.id] = task

            # 通知被分配的Agent
            target_agent = self.agents[message.to_agent]
            if hasattr(target_agent, 'receive_task'):
                await target_agent.receive_task(task)

            logger.info(f"任务分配: {task.task_name} -> {target_agent.name}")

        except Exception as e:
            logger.error(f"处理任务分配失败: {e}")

    async def _handle_task_completion(self, message: AgentMessage):
        """处理任务完成消息"""
        try:
            completion_data = message.content
            task_id = completion_data["task_id"]

            if task_id in self.task_assignments:
                task = self.task_assignments[task_id]
                task.status = "completed"
                task.result = completion_data.get("result")

                logger.info(f"任务完成: {task.task_name}")

                # 通知协调者
                coordinator = self._find_coordinator()
                if coordinator and coordinator.id != message.from_agent:
                    await self.send_message(AgentMessage(
                        from_agent=message.from_agent,
                        to_agent=coordinator.id,
                        message_type=MessageType.STATUS_UPDATE,
                        content={"type": "task_completed", "task_id": task_id}
                    ))

        except Exception as e:
            logger.error(f"处理任务完成失败: {e}")

    async def _handle_request_help(self, message: AgentMessage):
        """处理请求帮助消息"""
        try:
            help_request = message.content
            problem_type = help_request.get("problem_type", "general")

            # 寻找合适的专家Agent
            specialist = self._find_specialist(problem_type)

            if specialist:
                await self.send_message(AgentMessage(
                    from_agent="system",
                    to_agent=specialist.id,
                    message_type=MessageType.COLLABORATION_REQUEST,
                    content={
                        "type": "help_request",
                        "requester": message.from_agent,
                        "problem": help_request
                    }
                ))

                logger.info(f"请求帮助: {message.from_agent} -> {specialist.name}")

        except Exception as e:
            logger.error(f"处理请求帮助失败: {e}")

    async def _handle_status_update(self, message: AgentMessage):
        """处理状态更新消息"""
        logger.debug(f"状态更新: {message.from_agent} - {message.content}")

    async def _handle_error_report(self, message: AgentMessage):
        """处理错误报告消息"""
        logger.error(f"Agent错误报告: {message.from_agent} - {message.content}")

    def _find_coordinator(self) -> Optional[BaseAgent]:
        """查找协调者Agent"""
        for agent in self.agents.values():
            if getattr(agent, 'collaboration_role', None) == CollaborationRole.COORDINATOR:
                return agent
        return None

    def _find_specialist(self, problem_type: str) -> Optional[BaseAgent]:
        """查找专家Agent"""
        for agent in self.agents.values():
            role = getattr(agent, 'collaboration_role', None)
            if role == CollaborationRole.SPECIALIST:
                # 检查专业领域
                specialties = getattr(agent, 'specialties', [])
                if problem_type in specialties or 'general' in specialties:
                    return agent
        return None

    async def assign_task(self, task_name: str, task_description: str,
                         assigned_to: str, assigned_by: str = "system",
                         parameters: Dict[str, Any] = None) -> str:
        """分配任务"""
        message = AgentMessage(
            from_agent=assigned_by,
            to_agent=assigned_to,
            message_type=MessageType.TASK_ASSIGNMENT,
            content={
                "task_name": task_name,
                "task_description": task_description,
                "parameters": parameters or {}
            }
        )

        await self.send_message(message)
        return message.id

    async def create_collaboration_session(self, session_name: str,
                                         participant_agents: List[str],
                                         coordinator_agent: str = None) -> str:
        """创建协作会话"""
        session_id = str(uuid.uuid4())

        session = {
            "id": session_id,
            "name": session_name,
            "participants": participant_agents,
            "coordinator": coordinator_agent or participant_agents[0],
            "status": "active",
            "created_at": datetime.utcnow(),
            "messages": [],
            "shared_context": {}
        }

        self.collaboration_sessions[session_id] = session

        # 通知所有参与者
        for agent_id in participant_agents:
            await self.send_message(AgentMessage(
                from_agent="system",
                to_agent=agent_id,
                message_type=MessageType.STATUS_UPDATE,
                content={
                    "type": "session_created",
                    "session_id": session_id,
                    "session_name": session_name
                }
            ))

        logger.info(f"创建协作会话: {session_name} (参与者: {len(participant_agents)})")
        return session_id

    async def execute_collaborative_workflow(self, workflow_config: Dict[str, Any]) -> Dict[str, Any]:
        """执行协作工作流"""
        try:
            workflow_name = workflow_config["name"]
            tasks = workflow_config["tasks"]

            # 创建协作会话
            session_id = await self.create_collaboration_session(
                f"协作工作流: {workflow_name}",
                [task["agent_id"] for task in tasks]
            )

            results = {}

            # 执行任务
            for task in tasks:
                agent_id = task["agent_id"]
                task_name = task["task_name"]
                task_params = task.get("parameters", {})

                # 分配任务
                await self.assign_task(
                    task_name=task_name,
                    task_description=task.get("description", ""),
                    assigned_to=agent_id,
                    parameters=task_params
                )

                # 等待任务完成（简化实现）
                await asyncio.sleep(0.1)

                # 获取结果
                task_results = await self._get_task_results(agent_id, task_name)
                results[task_name] = task_results

            logger.info(f"协作工作流执行完成: {workflow_name}")
            return {
                "session_id": session_id,
                "workflow_name": workflow_name,
                "results": results,
                "status": "completed"
            }

        except Exception as e:
            logger.error(f"协作工作流执行失败: {e}")
            return {"status": "failed", "error": str(e)}

    async def _get_task_results(self, agent_id: str, task_name: str) -> Any:
        """获取任务结果（简化实现）"""
        # 这里应该实际等待Agent完成任务并返回结果
        agent = self.agents.get(agent_id)
        if agent:
            # 模拟Agent执行任务
            result = await agent.execute([f"执行任务: {task_name}"])
            return result.get("result", "任务完成")
        return None

    def get_collaboration_stats(self) -> Dict[str, Any]:
        """获取协作统计信息"""
        active_sessions = len([s for s in self.collaboration_sessions.values()
                             if s["status"] == "active"])

        task_stats = {
            "total": len(self.task_assignments),
            "completed": len([t for t in self.task_assignments.values()
                            if t.status == "completed"]),
            "in_progress": len([t for t in self.task_assignments.values()
                              if t.status == "in_progress"]),
            "failed": len([t for t in self.task_assignments.values()
                         if t.status == "failed"])
        }

        return {
            "registered_agents": len(self.agents),
            "active_sessions": active_sessions,
            "total_messages": len(self.message_queue),
            "task_stats": task_stats,
            "agent_roles": {
                role.value: len([a for a in self.agents.values()
                               if getattr(a, 'collaboration_role', None) == role])
                for role in CollaborationRole
            }
        }


# 扩展Agent基类以支持协作
class CollaborativeAgent(BaseAgent):
    """支持协作的Agent"""

    def __init__(self, name: str, description: str = "",
                 role: CollaborationRole = CollaborationRole.EXECUTOR,
                 specialties: List[str] = None):
        super().__init__(name, description)
        self.collaboration_role = role
        self.specialties = specialties or []
        self.collaboration_manager: Optional[AgentCollaboration] = None
        self.assigned_tasks: List[TaskAssignment] = []

    async def receive_task(self, task: TaskAssignment):
        """接收任务分配"""
        self.assigned_tasks.append(task)
        task.status = "in_progress"

        logger.info(f"Agent {self.name} 接收任务: {task.task_name}")

        # 执行任务
        try:
            result = await self._execute_assigned_task(task)
            task.result = result
            task.status = "completed"

            # 报告任务完成
            if self.collaboration_manager:
                await self.collaboration_manager.send_message(AgentMessage(
                    from_agent=self.id,
                    to_agent=task.assigned_by,
                    message_type=MessageType.TASK_COMPLETION,
                    content={
                        "task_id": task.id,
                        "result": result
                    }
                ))

        except Exception as e:
            task.status = "failed"
            logger.error(f"任务执行失败: {task.task_name} - {e}")

            # 报告错误
            if self.collaboration_manager:
                await self.collaboration_manager.send_message(AgentMessage(
                    from_agent=self.id,
                    to_agent=task.assigned_by,
                    message_type=MessageType.ERROR_REPORT,
                    content={
                        "task_id": task.id,
                        "error": str(e)
                    }
                ))

    async def _execute_assigned_task(self, task: TaskAssignment) -> Any:
        """执行分配的任务"""
        # 构造执行参数
        messages = [f"{task.task_description}"]
        metadata = task.parameters

        # 执行Agent
        result = await self.execute(messages, metadata)
        return result.get("result", "任务完成")

    async def request_collaboration(self, problem_type: str, description: str) -> bool:
        """请求协作帮助"""
        if not self.collaboration_manager:
            return False

        message = AgentMessage(
            from_agent=self.id,
            to_agent="system",  # 发送给系统，由系统分配专家
            message_type=MessageType.REQUEST_HELP,
            content={
                "problem_type": problem_type,
                "description": description
            }
        )

        return await self.collaboration_manager.send_message(message)


# 全局协作管理器实例
collaboration_manager = AgentCollaboration()