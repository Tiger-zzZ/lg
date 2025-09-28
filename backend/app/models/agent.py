from sqlalchemy import Column, String, DateTime, Boolean, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid

from app.core.database import Base


class Agent(Base):
    """Agent模型"""
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    type = Column(String(50), nullable=False)  # 'rag', 'chat', 'search', etc.

    # Agent配置
    config = Column(JSON, nullable=True, default={})  # 存储Agent的配置参数

    # 状态和元数据
    is_active = Column(Boolean, default=True)
    status = Column(String(20), default='idle')  # 'idle', 'running', 'error', 'disabled'

    # 关联用户
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    user = relationship("User", back_populates="agents")

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)

    def __repr__(self):
        return f"<Agent {self.name} ({self.type})>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "name": self.name,
            "description": self.description,
            "type": self.type,
            "config": self.config,
            "is_active": self.is_active,
            "status": self.status,
            "user_id": str(self.user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
        }


class AgentExecution(Base):
    """Agent执行记录模型"""
    __tablename__ = "agent_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey('agents.id'), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # 执行信息
    input_data = Column(JSON, nullable=False)  # 输入的消息和参数
    output_data = Column(JSON, nullable=True)  # 输出结果
    status = Column(String(20), default='pending')  # 'pending', 'running', 'completed', 'failed'
    error_message = Column(Text, nullable=True)

    # 性能指标
    duration_ms = Column(String(50), nullable=True)  # 执行时长（毫秒）
    tokens_used = Column(String(50), nullable=True)  # 使用的token数量

    # 时间戳
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # 关联
    agent = relationship("Agent")
    user = relationship("User")

    def __repr__(self):
        return f"<AgentExecution {self.id} - {self.status}>"

    def to_dict(self):
        """转换为字典格式"""
        return {
            "id": str(self.id),
            "agent_id": str(self.agent_id),
            "user_id": str(self.user_id),
            "input_data": self.input_data,
            "output_data": self.output_data,
            "status": self.status,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }