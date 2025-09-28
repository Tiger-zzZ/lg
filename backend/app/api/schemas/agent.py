from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime


class AgentCreateRequest(BaseModel):
    """创建Agent请求"""
    type: str = Field(..., description="Agent类型")
    name: Optional[str] = Field(None, description="自定义名称")
    description: Optional[str] = Field(None, description="Agent描述")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Agent配置")


class AgentConfigRequest(BaseModel):
    """Agent配置请求"""
    config: Dict[str, Any] = Field(..., description="Agent配置")


class AgentExecuteRequest(BaseModel):
    """执行Agent请求"""
    messages: List[str] = Field(..., description="输入消息")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class AgentResponse(BaseModel):
    """Agent响应"""
    id: str
    name: str
    description: Optional[str] = None
    type: str
    config: Optional[Dict[str, Any]] = None
    is_active: bool = True
    status: str = "idle"
    created_at: datetime
    updated_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None

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


class AgentExecutionHistoryResponse(BaseModel):
    """Agent执行历史响应"""
    id: str
    agent_id: str
    input_data: Dict[str, Any]
    output_data: Optional[Dict[str, Any]] = None
    status: str
    error_message: Optional[str] = None
    duration_ms: Optional[str] = None
    started_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True