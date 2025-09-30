"""工作流相关数据库模型"""
from sqlalchemy import Column, String, DateTime, Text, JSON, ForeignKey, Integer, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class WorkflowDefinition(Base):
    """工作流定义模型"""
    __tablename__ = "workflow_definitions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # 工作流配置
    nodes = Column(JSON, nullable=False)  # 节点定义
    edges = Column(JSON, nullable=False, default=[])  # 连接关系
    flow_metadata = Column(JSON, nullable=True, default={})

    # 版本控制
    version = Column(Integer, default=1)
    is_active = Column(String(20), default=True)

    # 关联用户
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="workflows")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<WorkflowDefinition {self.name} v{self.version}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "nodes": self.nodes,
            "edges": self.edges,
            "metadata": self.flow_metadata,
            "version": self.version,
            "is_active": self.is_active,
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class FlowExecution(Base):
    """工作流执行记录模型"""
    __tablename__ = "flow_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    flow_id = Column(String(255), nullable=False, index=True)  # 工作流定义ID
    workflow_id = Column(UUID(as_uuid=True), ForeignKey('workflow_definitions.id'), nullable=True)

    # 执行信息
    status = Column(String(20), default='pending', index=True)  # pending, running, paused, completed, failed, cancelled
    current_node = Column(String(255), nullable=True)  # 当前执行节点

    # 上下文数据
    context_variables = Column(JSON, nullable=True, default={})
    loop_counters = Column(JSON, nullable=True, default={})
    branch_history = Column(JSON, nullable=True, default=[])
    execution_path = Column(JSON, nullable=True, default=[])
    checkpoints = Column(JSON, nullable=True, default={})

    # 执行结果
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    error_details = Column(JSON, nullable=True)

    # 性能指标
    duration_ms = Column(Float, nullable=True)  # 执行时长（毫秒）
    node_executions = Column(Integer, default=0)  # 执行节点数

    # 关联
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True)
    user = relationship("User")
    workflow = relationship("WorkflowDefinition")

    # 时间戳
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<FlowExecution {self.id} - {self.status}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "flow_id": self.flow_id,
            "workflow_id": str(self.workflow_id) if self.workflow_id else None,
            "status": self.status,
            "current_node": self.current_node,
            "context_variables": self.context_variables,
            "loop_counters": self.loop_counters,
            "branch_history": self.branch_history,
            "execution_path": self.execution_path,
            "result": self.result,
            "error_message": self.error_message,
            "error_details": self.error_details,
            "duration_ms": self.duration_ms,
            "node_executions": self.node_executions,
            "user_id": str(self.user_id) if self.user_id else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExecutionLog(Base):
    """工作流执行日志"""
    __tablename__ = "execution_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), ForeignKey('flow_executions.id'), nullable=False, index=True)

    # 日志信息
    node_id = Column(String(255), nullable=True)
    node_name = Column(String(255), nullable=True)
    log_level = Column(String(20), default='info')  # debug, info, warning, error
    message = Column(Text, nullable=False)
    details = Column(JSON, nullable=True)

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关联
    execution = relationship("FlowExecution")

    def __repr__(self):
        return f"<ExecutionLog {self.id} - {self.log_level}>"

    def to_dict(self):
        return {
            "id": str(self.id),
            "execution_id": str(self.execution_id),
            "node_id": self.node_id,
            "node_name": self.node_name,
            "log_level": self.log_level,
            "message": self.message,
            "details": self.details,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
