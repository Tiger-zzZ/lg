from typing import Dict, Type, Optional, Any
from app.agents.base import BaseAgent
from app.agents.implementations import (
    ResearchAgent, CodingAgent, WritingAgent,
    SearchAgent, ChatAgent, DataAnalystAgent
)
from app.agents.rag_agent import RAGAgent
from app.agents.configurable import create_configurable_agent
from app.agents.config import config_manager


class AgentManager:
    """Agent管理器"""

    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}

        # 保留旧的Agent类映射（用于向后兼容）
        self._agent_types: Dict[str, Type[BaseAgent]] = {
            "search": SearchAgent,
            "chat": ChatAgent,
            "rag": RAGAgent,
            "research": ResearchAgent,
            "coding": CodingAgent,
            "writing": WritingAgent,
            "data_analyst": DataAnalystAgent,  # 新增数据分析师
        }

        # 配置驱动的Agent类型（优先使用）
        self._configurable_types = {
            "search", "chat", "rag", "research", "coding", "writing"
        }

    def create_agent(
        self,
        agent_type: str,
        custom_config: Optional[Dict[str, Any]] = None,
        use_legacy: bool = False
    ) -> BaseAgent:
        """
        创建Agent实例

        Args:
            agent_type: Agent类型
            custom_config: 自定义配置（可选）
            use_legacy: 是否使用旧的实现（默认False，使用新的配置驱动实现）

        Returns:
            BaseAgent: Agent实例

        Raises:
            ValueError: 如果Agent类型不存在
        """
        if agent_type not in self._agent_types:
            raise ValueError(f"未知的Agent类型: {agent_type}")

        # 优先使用配置驱动的实现（除非明确要求使用旧实现）
        if not use_legacy and agent_type in self._configurable_types:
            agent = create_configurable_agent(agent_type, custom_config)
        else:
            # 使用旧的实现（向后兼容）
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
        # 使用配置管理器获取类型信息
        all_types = config_manager.get_all_type_info()

        # 返回类型描述字典（保持API兼容）
        return {
            agent_type: f"{info['name']} - {info['description']}"
            for agent_type, info in all_types.items()
        }

    def remove_agent(self, agent_id: str) -> bool:
        """移除Agent"""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False


# 全局Agent管理器实例
agent_manager = AgentManager()
