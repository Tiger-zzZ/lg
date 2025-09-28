from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class AgentCreateRequest(BaseModel):
    """创建Agent请求"""
    type: str = Field(..., description="Agent类型")
    name: Optional[str] = Field(None, description="自定义名称")


class AgentExecuteRequest(BaseModel):
    """执行Agent请求"""
    messages: List[str] = Field(..., description="输入消息")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class AgentResponse(BaseModel):
    """Agent响应"""
    id: str
    name: str
    description: str
    type: str
    created_at: datetime
    status: str = "idle"

    class Config:
        from_attributes = True


class AgentExecutionResponse(BaseModel):
    """Agent执行响应"""
    execution_id: str
    agent_id: str
    agent_name: str
    status: str
    result: str
    metadata: Dict[str, Any]
    duration: Optional[float] = None