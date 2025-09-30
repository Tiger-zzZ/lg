"""
Agent外部工具系统
提供标准化的工具接口和常用工具实现
"""

from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
import asyncio
import json

from app.core.logging import logger


class ToolType(Enum):
    """工具类型"""
    WEB_SEARCH = "web_search"
    FILE_OPERATION = "file_operation"
    API_CALL = "api_call"
    DATA_PROCESSING = "data_processing"
    DATABASE_QUERY = "database_query"
    CALCULATION = "calculation"


@dataclass
class ToolResult:
    """工具执行结果"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class BaseTool(ABC):
    """基础工具类"""

    def __init__(self, name: str, description: str, tool_type: ToolType):
        self.name = name
        self.description = description
        self.tool_type = tool_type
        self.enabled = True

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """执行工具"""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具参数架构"""
        return {
            "name": self.name,
            "description": self.description,
            "type": self.tool_type.value,
            "parameters": self.get_parameters()
        }

    @abstractmethod
    def get_parameters(self) -> Dict[str, Any]:
        """获取工具参数定义"""
        pass


class ToolManager:
    """工具管理器"""

    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._init_default_tools()

    def _init_default_tools(self):
        """初始化默认工具"""
        from .implementations import (
            CalculatorTool, WebSearchTool, FileReadTool,
            DataProcessingTool, DatabaseQueryTool
        )

        # 注册默认工具
        default_tools = [
            CalculatorTool(),
            WebSearchTool(),
            FileReadTool(),
            DataProcessingTool(),
            DatabaseQueryTool()
        ]

        for tool in default_tools:
            self.register_tool(tool)

    def register_tool(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name} ({tool.tool_type.value})")

    def get_tool(self, name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self._tools.get(name)

    def list_tools(self, tool_type: Optional[ToolType] = None) -> List[BaseTool]:
        """列出工具"""
        tools = list(self._tools.values())
        if tool_type:
            tools = [t for t in tools if t.tool_type == tool_type]
        return [t for t in tools if t.enabled]

    def get_available_tools_schema(self) -> List[Dict[str, Any]]:
        """获取可用工具的架构"""
        return [tool.get_schema() for tool in self.list_tools()]

    async def execute_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """执行工具"""
        tool = self.get_tool(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"工具不存在: {tool_name}"
            )

        if not tool.enabled:
            return ToolResult(
                success=False,
                error=f"工具已禁用: {tool_name}"
            )

        try:
            logger.info(f"执行工具: {tool_name}", parameters=kwargs)
            result = await tool.execute(**kwargs)
            logger.info(f"工具执行完成: {tool_name}", success=result.success)
            return result
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name}", error=str(e))
            return ToolResult(
                success=False,
                error=f"工具执行异常: {str(e)}"
            )


# 全局工具管理器实例
tool_manager = ToolManager()