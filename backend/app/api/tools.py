"""
Agent工具API路由
提供工具管理和执行的API接口
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.agents.tools import tool_manager, ToolType
from app.api.auth import get_current_user
from app.models.user import User
from app.core.logging import logger

router = APIRouter()


class ToolExecuteRequest(BaseModel):
    """工具执行请求"""
    tool_name: str
    parameters: Dict[str, Any] = {}


class ToolExecuteResponse(BaseModel):
    """工具执行响应"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = {}
    tool_name: str


@router.get("/tools", response_model=List[Dict[str, Any]])
async def list_available_tools(
    tool_type: Optional[str] = None,
    current_user: User = Depends(get_current_user)
):
    """获取可用工具列表"""
    try:
        # 过滤工具类型
        filter_type = None
        if tool_type:
            try:
                filter_type = ToolType(tool_type)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"无效的工具类型: {tool_type}")

        # 获取工具列表
        tools = tool_manager.list_tools(filter_type)

        return [
            {
                "name": tool.name,
                "description": tool.description,
                "type": tool.tool_type.value,
                "enabled": tool.enabled,
                "parameters": tool.get_parameters()
            }
            for tool in tools
        ]

    except Exception as e:
        logger.error(f"获取工具列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取工具列表失败")


@router.get("/tools/schema")
async def get_tools_schema(current_user: User = Depends(get_current_user)):
    """获取所有工具的架构信息"""
    try:
        schema = tool_manager.get_available_tools_schema()
        return {
            "tools": schema,
            "tool_types": [t.value for t in ToolType],
            "total_count": len(schema)
        }

    except Exception as e:
        logger.error(f"获取工具架构失败: {e}")
        raise HTTPException(status_code=500, detail="获取工具架构失败")


@router.post("/tools/execute", response_model=ToolExecuteResponse)
async def execute_tool(
    request: ToolExecuteRequest,
    current_user: User = Depends(get_current_user)
):
    """执行工具"""
    try:
        # 执行工具
        result = await tool_manager.execute_tool(
            request.tool_name,
            **request.parameters
        )

        return ToolExecuteResponse(
            success=result.success,
            data=result.data,
            error=result.error,
            metadata=result.metadata or {},
            tool_name=request.tool_name
        )

    except Exception as e:
        logger.error(f"执行工具失败: {request.tool_name}, 错误: {e}")
        raise HTTPException(status_code=500, detail=f"执行工具失败: {str(e)}")


@router.get("/tools/{tool_name}")
async def get_tool_info(
    tool_name: str,
    current_user: User = Depends(get_current_user)
):
    """获取特定工具的详细信息"""
    try:
        tool = tool_manager.get_tool(tool_name)
        if not tool:
            raise HTTPException(status_code=404, detail=f"工具不存在: {tool_name}")

        return {
            "name": tool.name,
            "description": tool.description,
            "type": tool.tool_type.value,
            "enabled": tool.enabled,
            "schema": tool.get_schema()
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取工具信息失败: {tool_name}, 错误: {e}")
        raise HTTPException(status_code=500, detail="获取工具信息失败")


@router.get("/tools/types")
async def get_tool_types(current_user: User = Depends(get_current_user)):
    """获取可用的工具类型"""
    return {
        "tool_types": [
            {
                "value": t.value,
                "name": t.value.replace("_", " ").title()
            }
            for t in ToolType
        ]
    }