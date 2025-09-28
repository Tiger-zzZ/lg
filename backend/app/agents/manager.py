from typing import Dict, Type
from .base import BaseAgent
from .implementations import ResearchAgent, CodingAgent, WritingAgent
from .rag_agent import RAGAgent


class AgentManager:
    """Agent管理器"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self._agent_types: Dict[str, Type[BaseAgent]] = {
            "research": ResearchAgent,
            "coding": CodingAgent,
            "writing": WritingAgent,
            "rag": RAGAgent,
        }

    def create_agent(self, agent_type: str) -> BaseAgent:
        """创建Agent实例"""
        if agent_type not in self._agent_types:
            raise ValueError(f"未知的Agent类型: {agent_type}")

        agent_class = self._agent_types[agent_type]
        agent = agent_class()
        self._agents[agent.id] = agent

        return agent

    def get_agent(self, agent_id: str) -> BaseAgent:
        """获取Agent实例"""
        if agent_id not in self._agents:
            raise ValueError(f"Agent不存在: {agent_id}")

        return self._agents[agent_id]

    def list_agents(self) -> Dict[str, BaseAgent]:
        """列出所有Agent"""
        return self._agents.copy()

    def get_available_types(self) -> Dict[str, str]:
        """获取可用的Agent类型"""
        return {
            "research": "研究Agent - 用于信息研究和分析",
            "coding": "编程Agent - 用于代码生成和编程任务",
            "writing": "写作Agent - 用于文本创作和写作",
            "rag": "RAG Agent - 基于文档知识库的智能问答",
        }

    def remove_agent(self, agent_id: str) -> bool:
        """移除Agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False


# 全局Agent管理器实例
agent_manager = AgentManager()