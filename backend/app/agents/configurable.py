"""
可配置Agent实现 - 配置驱动的通用Agent

这个模块提供了基于配置的Agent实现，消除代码重复，提高可维护性。
"""

import asyncio
from typing import List, Dict, Any, Optional

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from app.agents.base import BaseAgent, AgentState
from app.agents.config import AgentConfig, config_manager
from app.rag.search import SemanticSearch
from app.core.config import settings
from app.core.logging import logger


class ConfigurableAgent(BaseAgent):
    """
    可配置的通用Agent基类

    通过配置而非继承来定义不同类型的Agent，大幅减少代码重复。
    """

    def __init__(self, agent_type: str, custom_config: Optional[Dict[str, Any]] = None):
        """
        初始化可配置Agent

        Args:
            agent_type: Agent类型（如 'chat', 'search', 'coding'等）
            custom_config: 自定义配置（可选），会覆盖默认配置
        """
        # 获取配置
        self.agent_type = agent_type
        self.config = config_manager.get_config(agent_type, custom_config)

        # 初始化基类
        super().__init__(
            name=self.config.name,
            description=self.config.description
        )

        # LLM实例（延迟初始化）
        self._llm = None

    def _get_llm(self) -> ChatOpenAI:
        """获取或创建LLM实例（懒加载）"""
        if self._llm is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ['', 'EMPTY', 'sk-your-openai-api-key-here']:
                raise ValueError(
                    "OpenAI API 密钥未配置。请在 .env 文件中设置有效的 OPENAI_API_KEY。"
                )

            llm_config = self.config.llm_config
            self._llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
                temperature=llm_config.temperature,
                max_tokens=llm_config.max_tokens,
                top_p=llm_config.top_p,
                frequency_penalty=llm_config.frequency_penalty,
                presence_penalty=llm_config.presence_penalty
            )

        return self._llm

    async def _process(self, state: AgentState) -> AgentState:
        """
        处理逻辑 - 子类可以覆盖此方法以实现特定逻辑

        默认实现：使用LLM进行对话
        """
        raise NotImplementedError("子类必须实现 _process 方法")


class ConfigurableChatAgent(ConfigurableAgent):
    """
    基于配置的对话类Agent

    适用于：chat, coding, writing 等纯对话类型的Agent
    """

    async def _process(self, state: AgentState) -> AgentState:
        """对话处理逻辑"""
        try:
            if not state["messages"]:
                raise ValueError("没有对话消息")

            current_message = state["messages"][-1]
            chat_history = state["messages"][:-1]

            logger.info(f"{self.name} 处理对话: {current_message[:100]}...")

            # 生成AI回复
            response = await self._generate_chat_response(current_message, chat_history)

            # 更新状态
            updated_messages = state["messages"].copy()
            updated_messages.append(response)

            updated_metadata = {
                **state["metadata"],
                "response_length": len(response),
                "conversation_turns": len(updated_messages) // 2
            }

            logger.info(f"{self.name} 对话处理完成")

            return {
                **state,
                "messages": updated_messages,
                "result": response,
                "metadata": updated_metadata
            }

        except Exception as e:
            logger.error(f"{self.name} 处理失败: {str(e)}")
            error_message = f"{self.config.emoji} 抱歉，在处理您的消息时遇到了问题：{str(e)}"

            return {
                **state,
                "result": error_message,
                "status": "error",
                "metadata": {
                    **state["metadata"],
                    "error": str(e)
                }
            }

    async def _generate_chat_response(self, message: str, chat_history: List[str]) -> str:
        """生成对话回复"""
        try:
            # 构建系统提示
            messages = [SystemMessage(content=self.config.system_prompt)]

            # 添加对话历史（限制长度避免token超限）
            if chat_history:
                history_pairs = []
                for i in range(0, len(chat_history), 2):
                    if i + 1 < len(chat_history):
                        history_pairs.append((chat_history[i], chat_history[i + 1]))

                # 只保留最近的几轮对话
                recent_history = history_pairs[-3:] if len(history_pairs) > 3 else history_pairs

                for user_msg, ai_msg in recent_history:
                    messages.append(HumanMessage(content=user_msg))
                    messages.append(AIMessage(content=ai_msg))

            # 添加当前消息
            messages.append(HumanMessage(content=message))

            # 调用LLM
            llm = self._get_llm()
            response = await llm.ainvoke(messages)

            # 添加emoji前缀（如果配置了）
            if self.config.emoji and self.config.emoji != "🤖":
                return f"{self.config.emoji} {response.content}"

            return response.content

        except Exception as e:
            logger.error(f"生成对话回复失败: {str(e)}")
            return f"抱歉，我在处理您的消息时遇到了技术问题。请稍后重试。"


class ConfigurableSearchAgent(ConfigurableAgent):
    """
    基于配置的搜索类Agent

    适用于：search, research, rag 等需要搜索功能的Agent
    """

    def __init__(self, agent_type: str, custom_config: Optional[Dict[str, Any]] = None):
        super().__init__(agent_type, custom_config)
        self.search_engine = SemanticSearch()

    async def _process(self, state: AgentState) -> AgentState:
        """搜索处理逻辑"""
        try:
            if not state["messages"]:
                raise ValueError("没有搜索查询")

            query = state["messages"][-1]
            logger.info(f"{self.name} 处理查询: {query}")

            # 执行文档搜索
            search_results = await self.search_engine.hybrid_search(
                query=query,
                top_k=8,
                keyword_weight=0.4,
                semantic_weight=0.6,
                filter_metadata=state["metadata"].get("filter_metadata")
            )

            if not search_results:
                result = f"{self.config.emoji} 搜索结果\n\n未找到与查询 '{query}' 相关的文档内容。\n\n建议：\n• 尝试使用不同的关键词\n• 检查是否已上传相关文档\n• 使用更通用的搜索词"
            else:
                # 使用AI分析和总结搜索结果
                result = await self._generate_search_summary(query, search_results)

            # 更新状态
            updated_metadata = {
                **state["metadata"],
                "search_results": [
                    {
                        "document_id": r.document_id,
                        "chunk_index": r.chunk_index,
                        "score": r.score,
                        "content_preview": r.content[:150] + "..." if len(r.content) > 150 else r.content
                    }
                    for r in search_results
                ],
                "results_count": len(search_results)
            }

            logger.info(f"{self.name} 完成，找到 {len(search_results)} 个结果")

            return {
                **state,
                "result": result,
                "metadata": updated_metadata
            }

        except Exception as e:
            logger.error(f"{self.name} 处理失败: {str(e)}")
            error_message = f"{self.config.emoji} 搜索过程中遇到错误：{str(e)}"

            return {
                **state,
                "result": error_message,
                "status": "error",
                "metadata": {
                    **state["metadata"],
                    "error": str(e)
                }
            }

    async def _generate_search_summary(self, query: str, search_results: list) -> str:
        """生成搜索结果摘要"""
        try:
            # 构建搜索结果文本
            results_text = f"搜索查询: {query}\n找到 {len(search_results)} 个相关结果:\n\n"

            for i, result in enumerate(search_results[:5], 1):
                results_text += f"结果 {i} (相似度: {result.score:.2f}):\n{result.content}\n\n---\n\n"

            # 使用AI生成搜索摘要（使用配置的system_prompt）
            user_prompt = f"""
请为以下搜索结果生成摘要：

{results_text}

请生成一个结构化的搜索结果摘要。
"""

            messages = [
                SystemMessage(content=self.config.system_prompt),
                HumanMessage(content=user_prompt)
            ]

            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, messages)

            return f"{self.config.emoji} 搜索结果摘要\n\n{response.content}"

        except Exception as e:
            logger.error(f"生成搜索摘要失败: {str(e)}")
            # 如果AI摘要失败，返回简单的结果列表
            simple_summary = f"{self.config.emoji} 搜索结果 (共 {len(search_results)} 条)\n\n"
            for i, result in enumerate(search_results[:3], 1):
                simple_summary += f"{i}. 相似度: {result.score:.2f}\n{result.content[:200]}...\n\n"
            return simple_summary


# ===========================
# Agent工厂函数
# ===========================

def create_configurable_agent(
    agent_type: str,
    custom_config: Optional[Dict[str, Any]] = None
) -> BaseAgent:
    """
    工厂函数：创建可配置的Agent实例

    Args:
        agent_type: Agent类型
        custom_config: 自定义配置（可选）

    Returns:
        BaseAgent: Agent实例

    Raises:
        ValueError: 如果Agent类型不支持
    """
    # 获取配置以确定Agent类别
    config = config_manager.get_config(agent_type, custom_config)

    # 根据能力判断使用哪个Agent类
    from app.agents.config import AgentCapability

    if AgentCapability.SEARCH in config.capabilities:
        # 搜索类Agent（search, research, rag）
        return ConfigurableSearchAgent(agent_type, custom_config)
    else:
        # 对话类Agent（chat, coding, writing）
        return ConfigurableChatAgent(agent_type, custom_config)
