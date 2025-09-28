from typing import TypedDict, Dict, Any, List
from langgraph import StateGraph
from abc import ABC, abstractmethod
import uuid
import time
import asyncio
from datetime import datetime

from ..core.logging import logger


class AgentState(TypedDict):
    """Agent状态定义"""
    messages: List[str]
    result: str
    metadata: Dict[str, Any]
    status: str  # pending, running, completed, failed
    execution_id: str


class BaseAgent(ABC):
    """基础Agent类"""

    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.id = str(uuid.uuid4())
        self.created_at = datetime.utcnow()
        self.graph = self._create_graph()

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