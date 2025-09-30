from typing import TypedDict, Dict, Any, List, Optional
from langgraph.graph import StateGraph
from abc import ABC, abstractmethod
import uuid
import time
import asyncio
from datetime import datetime

from app.core.logging import logger


class AgentState(TypedDict):
    """Agent状态定义"""
    messages: List[str]
    result: str
    metadata: Dict[str, Any]
    status: str  # pending, running, completed, failed
    execution_id: str
    tool_results: Optional[List[Dict[str, Any]]]  # 工具执行结果


class BaseAgent(ABC):
    """基础Agent类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.enabled_tools: List[str] = []  # 启用的工具列表
        self.graph = self._create_graph()

    def enable_tools(self, tool_names: List[str]):
        """启用指定工具"""
        self.enabled_tools = tool_names
        logger.info(f"Agent {self.name} 启用工具: {tool_names}")

    def disable_tools(self):
        """禁用所有工具"""
        self.enabled_tools = []
        logger.info(f"Agent {self.name} 禁用所有工具")

    async def _use_tool(self, tool_name: str, **kwargs) -> Dict[str, Any]:
        """使用工具"""
        if tool_name not in self.enabled_tools:
            return {
                "success": False,
                "error": f"工具未启用: {tool_name}",
                "tool_name": tool_name
            }

        try:
            from app.agents.tools import tool_manager
            result = await tool_manager.execute_tool(tool_name, **kwargs)

            return {
                "success": result.success,
                "data": result.data,
                "error": result.error,
                "metadata": result.metadata,
                "tool_name": tool_name
            }
        except Exception as e:
            logger.error(f"工具使用失败: {tool_name}", error=str(e))
            return {
                "success": False,
                "error": f"工具执行异常: {str(e)}",
                "tool_name": tool_name
            }

    def _create_graph(self) -> StateGraph:
        """创建LangGraph工作流"""
        workflow = StateGraph(AgentState)

        # 添加节点
        workflow.add_node("initialize", self._initialize)
        workflow.add_node("process", self._process)
        workflow.add_node("finalize", self._finalize)

        # 设置边
        workflow.set_entry_point("initialize")
        workflow.add_edge("initialize", "process")
        workflow.add_edge("process", "finalize")
        workflow.set_finish_point("finalize")

        return workflow.compile()

    async def _initialize(self, state: AgentState) -> AgentState:
        """初始化阶段"""
        logger.info(f"Agent {self.name} initializing", agent_id=self.id)

        return {
            **state,
            "status": "running",
            "execution_id": str(uuid.uuid4()),
            "metadata": {
                **state.get("metadata", {}),
                "agent_name": self.name,
                "agent_id": self.id,
                "start_time": time.time(),
            }
        }

    @abstractmethod
    async def _process(self, state: AgentState) -> AgentState:
        """处理阶段 - 子类必须实现"""
        pass

    async def _finalize(self, state: AgentState) -> AgentState:
        """完成阶段"""
        end_time = time.time()
        start_time = state["metadata"].get("start_time", end_time)
        duration = end_time - start_time

        logger.info(
            f"Agent {self.name} completed",
            agent_id=self.id,
            execution_id=state["execution_id"],
            duration=duration
        )

        return {
            **state,
            "status": "completed",
            "metadata": {
                **state["metadata"],
                "end_time": end_time,
                "duration": duration,
            }
        }

    async def execute(self, messages: List[str], metadata: Dict[str, Any] = None) -> AgentState:
        """执行Agent"""
        initial_state: AgentState = {
            "messages": messages,
            "result": "",
            "metadata": metadata or {},
            "status": "pending",
            "execution_id": "",
            "tool_results": [],
        }

        try:
            result = await self.graph.ainvoke(initial_state)
            return result
        except Exception as e:
            logger.error(
                f"Agent {self.name} execution failed",
                agent_id=self.id,
                error=str(e)
            )
            return {
                **initial_state,
                "status": "failed",
                "result": f"执行失败: {str(e)}",
                "metadata": {
                    **initial_state["metadata"],
                    "error": str(e),
                }
            }


class SimpleAgent(BaseAgent):
    """简单Agent实现"""

    async def _process(self, state: AgentState) -> AgentState:
        """简单的处理逻辑"""
        if not state["messages"]:
            return {
                **state,
                "result": "没有收到消息"
            }

        last_message = state["messages"][-1]
        result = f"[{self.name}] 处理消息: {last_message}"

        # 模拟处理时间
        await asyncio.sleep(0.1)

        return {
            **state,
            "result": result
        }


class EchoAgent(BaseAgent):
    """回声Agent - 用于测试"""

    async def _process(self, state: AgentState) -> AgentState:
        """回声处理"""
        messages = state["messages"]
        result = f"Echo: {' | '.join(messages)}"

        return {
            **state,
            "result": result
        }