"""
Agent配置系统 - 配置驱动的Agent设计

这个模块提供了统一的Agent配置管理，支持：
- 默认配置定义
- 配置继承和覆盖
- 配置验证
- 动态配置加载
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum


class AgentCapability(str, Enum):
    """Agent能力枚举"""
    CONVERSATION = "conversation"
    SEARCH = "search"
    CODE_GENERATION = "code_generation"
    DATA_ANALYSIS = "data_analysis"
    WRITING = "writing"
    RESEARCH = "research"


@dataclass
class LLMConfig:
    """LLM配置"""
    temperature: float = 0.7
    max_tokens: int = 1000
    top_p: float = 1.0
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'LLMConfig':
        """从字典创建"""
        return cls(**{k: v for k, v in data.items() if k in cls.__annotations__})


@dataclass
class AgentConfig:
    """Agent配置"""
    name: str
    description: str
    system_prompt: str
    llm_config: LLMConfig = field(default_factory=LLMConfig)
    capabilities: List[AgentCapability] = field(default_factory=list)
    emoji: str = "🤖"
    color: str = "#1890ff"

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "name": self.name,
            "description": self.description,
            "system_prompt": self.system_prompt,
            "llm_config": self.llm_config.to_dict(),
            "capabilities": [c.value for c in self.capabilities],
            "emoji": self.emoji,
            "color": self.color
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentConfig':
        """从字典创建"""
        llm_config = LLMConfig.from_dict(data.get("llm_config", {}))
        capabilities = [AgentCapability(c) for c in data.get("capabilities", [])]

        return cls(
            name=data.get("name", ""),
            description=data.get("description", ""),
            system_prompt=data.get("system_prompt", ""),
            llm_config=llm_config,
            capabilities=capabilities,
            emoji=data.get("emoji", "🤖"),
            color=data.get("color", "#1890ff")
        )

    def merge(self, other: Dict[str, Any]) -> 'AgentConfig':
        """合并配置，other中的值会覆盖当前配置"""
        current_dict = self.to_dict()

        # 合并LLM配置
        if "llm_config" in other:
            llm_config = {**current_dict["llm_config"], **other["llm_config"]}
            other = {**other, "llm_config": llm_config}

        # 合并其他字段
        merged = {**current_dict, **other}

        return AgentConfig.from_dict(merged)


# ===========================
# 默认Agent配置定义
# ===========================

DEFAULT_AGENT_CONFIGS: Dict[str, AgentConfig] = {
    "chat": AgentConfig(
        name="对话助手",
        description="通用的AI对话助手，能够进行自然语言对话和回答各种问题",
        system_prompt="""你是一个智能的AI助手，能够：
1. 进行自然、有帮助的对话
2. 回答各种问题和提供信息
3. 协助解决问题和提供建议
4. 保持友好、专业的语调

请根据用户的消息提供有用、准确的回复。如果不确定某些信息，请诚实说明。""",
        llm_config=LLMConfig(
            temperature=0.7,
            max_tokens=1000
        ),
        capabilities=[AgentCapability.CONVERSATION],
        emoji="💬",
        color="#52c41a"
    ),

    "search": AgentConfig(
        name="搜索助手",
        description="专门用于文档搜索和信息检索的智能助手",
        system_prompt="""你是一个搜索结果分析助手。请根据搜索结果生成一个有用的摘要，包括：
1. 简要概述找到的信息
2. 突出最相关的内容
3. 提供有条理的信息组织
4. 如果有多个来源，说明不同来源的内容

请保持摘要简洁但信息丰富。""",
        llm_config=LLMConfig(
            temperature=0.3,
            max_tokens=800
        ),
        capabilities=[AgentCapability.SEARCH, AgentCapability.CONVERSATION],
        emoji="🔍",
        color="#1890ff"
    ),

    "coding": AgentConfig(
        name="编程助手",
        description="专门用于代码生成和编程任务的Agent",
        system_prompt="""你是一个专业的编程助手，专门帮助用户：
1. 编写和优化代码
2. 解决编程问题
3. 解释代码概念和最佳实践
4. 提供代码示例和解决方案
5. 调试和错误排查

请提供清晰、实用的编程建议和代码示例。使用适当的代码格式和注释。""",
        llm_config=LLMConfig(
            temperature=0.3,
            max_tokens=2000
        ),
        capabilities=[AgentCapability.CODE_GENERATION, AgentCapability.CONVERSATION],
        emoji="💻",
        color="#722ed1"
    ),

    "writing": AgentConfig(
        name="写作助手",
        description="专门用于文本创作和写作的Agent",
        system_prompt="""你是一个专业的写作助手，专门帮助用户：
1. 创作各种类型的文档和文章
2. 改进和润色文本
3. 提供写作建议和技巧
4. 协助内容策划和结构化
5. 适应不同的写作风格和场景

请提供高质量、结构化的写作内容和建议。注意语言的流畅性和可读性。""",
        llm_config=LLMConfig(
            temperature=0.7,
            max_tokens=1500
        ),
        capabilities=[AgentCapability.WRITING, AgentCapability.CONVERSATION],
        emoji="✍️",
        color="#fa8c16"
    ),

    "research": AgentConfig(
        name="研究助手",
        description="专门用于信息研究和分析的Agent，基于文档搜索提供研究结果",
        system_prompt="""你是一个专业的研究助手，专门帮助用户：
1. 进行深入的信息研究
2. 分析和综合多个信息来源
3. 提供有依据的研究结论
4. 识别信息的可靠性和相关性
5. 生成结构化的研究报告

请基于搜索结果提供全面、准确的研究分析。""",
        llm_config=LLMConfig(
            temperature=0.3,
            max_tokens=1200
        ),
        capabilities=[AgentCapability.RESEARCH, AgentCapability.SEARCH, AgentCapability.CONVERSATION],
        emoji="🔬",
        color="#13c2c2"
    ),

    "rag": AgentConfig(
        name="文档问答",
        description="基于知识库的智能问答助手",
        system_prompt="""你是一个基于知识库的问答助手，请：
1. 根据检索到的文档内容回答问题
2. 确保答案准确并引用相关文档
3. 如果文档中没有相关信息，请说明
4. 提供清晰、易懂的解释

请始终基于提供的文档内容进行回答。""",
        llm_config=LLMConfig(
            temperature=0.3,
            max_tokens=1000
        ),
        capabilities=[AgentCapability.SEARCH, AgentCapability.CONVERSATION],
        emoji="📚",
        color="#eb2f96"
    ),

    "data_analyst": AgentConfig(
        name="数据分析师",
        description="专业的数据分析和可视化专家，擅长数据处理、统计分析和洞察发现",
        system_prompt="""你是一个专业的数据分析师，专门帮助用户：
1. 进行数据探索和分析
2. 提供统计分析方法和建议
3. 设计数据可视化方案
4. 解释分析结果和提供洞察
5. 推荐合适的分析工具和技术

请提供专业、准确的数据分析指导。""",
        llm_config=LLMConfig(
            temperature=0.5,
            max_tokens=1200
        ),
        capabilities=[AgentCapability.DATA_ANALYSIS, AgentCapability.CONVERSATION],
        emoji="📊",
        color="#faad14"
    ),
}


class AgentConfigManager:
    """Agent配置管理器"""

    def __init__(self):
        self._configs: Dict[str, AgentConfig] = DEFAULT_AGENT_CONFIGS.copy()

    def get_config(self, agent_type: str, custom_config: Optional[Dict[str, Any]] = None) -> AgentConfig:
        """
        获取Agent配置

        Args:
            agent_type: Agent类型
            custom_config: 自定义配置（会覆盖默认配置）

        Returns:
            AgentConfig: 合并后的配置

        Raises:
            ValueError: 如果Agent类型不存在
        """
        if agent_type not in self._configs:
            raise ValueError(f"未知的Agent类型: {agent_type}")

        base_config = self._configs[agent_type]

        # 如果有自定义配置，合并
        if custom_config:
            return base_config.merge(custom_config)

        return base_config

    def register_config(self, agent_type: str, config: AgentConfig):
        """
        注册新的Agent配置

        Args:
            agent_type: Agent类型
            config: Agent配置
        """
        self._configs[agent_type] = config

    def list_types(self) -> List[str]:
        """列出所有可用的Agent类型"""
        return list(self._configs.keys())

    def get_type_info(self, agent_type: str) -> Dict[str, Any]:
        """
        获取Agent类型信息

        Args:
            agent_type: Agent类型

        Returns:
            包含类型信息的字典
        """
        if agent_type not in self._configs:
            raise ValueError(f"未知的Agent类型: {agent_type}")

        config = self._configs[agent_type]
        return {
            "type": agent_type,
            "name": config.name,
            "description": config.description,
            "emoji": config.emoji,
            "color": config.color,
            "capabilities": [c.value for c in config.capabilities]
        }

    def get_all_type_info(self) -> Dict[str, Dict[str, Any]]:
        """获取所有Agent类型信息"""
        return {
            agent_type: self.get_type_info(agent_type)
            for agent_type in self._configs.keys()
        }


# 全局配置管理器实例
config_manager = AgentConfigManager()
