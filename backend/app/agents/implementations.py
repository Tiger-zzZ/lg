import asyncio
from typing import List

from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from app.agents.base import BaseAgent, AgentState
from app.rag.search import SemanticSearch
from app.core.config import settings
from app.core.logging import logger


class SearchAgent(BaseAgent):
    """搜索助手Agent - 专门用于文档搜索和信息检索"""

    def __init__(self):
        super().__init__(
            name="Search Agent",
            description="专门用于文档搜索和信息检索的智能助手"
        )
        self.search_engine = SemanticSearch()
        self._llm = None

    def _get_llm(self):
        """延迟初始化 ChatOpenAI"""
        if self._llm is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ['', 'EMPTY', 'sk-your-openai-api-key-here']:
                raise ValueError(
                    "OpenAI API 密钥未配置。请在 .env 文件中设置有效的 OPENAI_API_KEY。"
                )
            self._llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
                temperature=0.3,
                max_tokens=800
            )
        return self._llm

    async def _process(self, state: AgentState) -> AgentState:
        """搜索处理逻辑"""
        try:
            if not state["messages"]:
                raise ValueError("没有搜索查询")

            query = state["messages"][-1]
            logger.info(f"Search Agent 处理查询: {query}")

            # 执行文档搜索
            search_results = await self.search_engine.hybrid_search(
                query=query,
                top_k=8,
                keyword_weight=0.4,
                semantic_weight=0.6,
                filter_metadata=state["metadata"].get("filter_metadata")
            )

            if not search_results:
                result = f"🔍 搜索结果\n\n未找到与查询 '{query}' 相关的文档内容。\n\n建议：\n• 尝试使用不同的关键词\n• 检查是否已上传相关文档\n• 使用更通用的搜索词"
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

            logger.info(f"Search Agent 完成，找到 {len(search_results)} 个结果")

            return {
                **state,
                "result": result,
                "metadata": updated_metadata
            }

        except Exception as e:
            logger.error(f"Search Agent 处理失败: {str(e)}")
            error_message = f"🔍 搜索过程中遇到错误：{str(e)}"

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

            # 使用AI生成搜索摘要
            system_prompt = """你是一个搜索结果分析助手。请根据搜索结果生成一个有用的摘要，包括：
1. 简要概述找到的信息
2. 突出最相关的内容
3. 提供有条理的信息组织
4. 如果有多个来源，说明不同来源的内容

请保持摘要简洁但信息丰富。"""

            user_prompt = f"""
请为以下搜索结果生成摘要：

{results_text}

请生成一个结构化的搜索结果摘要。
"""

            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_prompt)
            ]

            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, messages)

            return f"🔍 搜索结果摘要\n\n{response.content}"

        except Exception as e:
            logger.error(f"生成搜索摘要失败: {str(e)}")
            # 如果AI摘要失败，返回简单的结果列表
            simple_summary = f"🔍 搜索结果 (共 {len(search_results)} 条)\n\n"
            for i, result in enumerate(search_results[:3], 1):
                simple_summary += f"{i}. 相似度: {result.score:.2f}\n{result.content[:200]}...\n\n"
            return simple_summary


class ChatAgent(BaseAgent):
    """对话助手Agent - 通用的AI对话助手"""

    def __init__(self):
        super().__init__(
            name="Chat Agent",
            description="通用的AI对话助手，能够进行自然语言对话和回答各种问题"
        )
        self._llm = None

    def _get_llm(self):
        """延迟初始化 ChatOpenAI"""
        if self._llm is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ['', 'EMPTY', 'sk-your-openai-api-key-here']:
                raise ValueError(
                    "OpenAI API 密钥未配置。请在 .env 文件中设置有效的 OPENAI_API_KEY。"
                )
            self._llm = ChatOpenAI(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
                temperature=0.7,
                max_tokens=1000
            )
        return self._llm

    async def _process(self, state: AgentState) -> AgentState:
        """对话处理逻辑"""
        try:
            if not state["messages"]:
                raise ValueError("没有对话消息")

            current_message = state["messages"][-1]
            chat_history = state["messages"][:-1]

            logger.info(f"Chat Agent 处理对话: {current_message[:100]}...")

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

            logger.info("Chat Agent 对话处理完成")

            return {
                **state,
                "messages": updated_messages,
                "result": response,
                "metadata": updated_metadata
            }

        except Exception as e:
            logger.error(f"Chat Agent 处理失败: {str(e)}")
            error_message = f"💬 抱歉，在处理您的消息时遇到了问题：{str(e)}"

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
            system_prompt = """你是一个智能的AI助手，能够：
1. 进行自然、有帮助的对话
2. 回答各种问题和提供信息
3. 协助解决问题和提供建议
4. 保持友好、专业的语调

请根据用户的消息提供有用、准确的回复。如果不确定某些信息，请诚实说明。"""

            messages = [SystemMessage(content=system_prompt)]

            # 添加对话历史 (限制长度避免token超限)
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
            response = await asyncio.to_thread(llm.invoke, messages)

            return response.content

        except Exception as e:
            logger.error(f"生成对话回复失败: {str(e)}")
            return "抱歉，我在处理您的消息时遇到了技术问题。请稍后重试。"


# 为向后兼容保留原有的Agent类，但用新的实现替换
class ResearchAgent(SearchAgent):
    """研究Agent - 使用搜索功能进行信息研究"""

    def __init__(self):
        super().__init__()
        self.name = "Research Agent"
        self.description = "专门用于信息研究和分析的Agent，基于文档搜索提供研究结果"


class CodingAgent(ChatAgent):
    """编程Agent - 专门处理编程相关问题"""

    def __init__(self):
        super().__init__()
        self.name = "Coding Agent"
        self.description = "专门用于代码生成和编程任务的Agent"

    async def _generate_chat_response(self, message: str, chat_history: List[str]) -> str:
        """重写以专注于编程任务"""
        try:
            system_prompt = """你是一个专业的编程助手，专门帮助用户：
1. 编写和优化代码
2. 解决编程问题
3. 解释代码概念和最佳实践
4. 提供代码示例和解决方案
5. 调试和错误排查

请提供清晰、实用的编程建议和代码示例。使用适当的代码格式和注释。"""

            messages = [SystemMessage(content=system_prompt)]

            # 添加对话历史
            if chat_history:
                history_pairs = []
                for i in range(0, len(chat_history), 2):
                    if i + 1 < len(chat_history):
                        history_pairs.append((chat_history[i], chat_history[i + 1]))

                recent_history = history_pairs[-2:] if len(history_pairs) > 2 else history_pairs

                for user_msg, ai_msg in recent_history:
                    messages.append(HumanMessage(content=user_msg))
                    messages.append(AIMessage(content=ai_msg))

            messages.append(HumanMessage(content=message))

            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, messages)

            return f"💻 {response.content}"

        except Exception as e:
            logger.error(f"生成编程回复失败: {str(e)}")
            return "💻 抱歉，我在处理您的编程问题时遇到了技术问题。请稍后重试。"


class WritingAgent(ChatAgent):
    """写作Agent - 专门处理写作和内容创作"""

    def __init__(self):
        super().__init__()
        self.name = "Writing Agent"
        self.description = "专门用于文本创作和写作的Agent"

    async def _generate_chat_response(self, message: str, chat_history: List[str]) -> str:
        """重写以专注于写作任务"""
        try:
            system_prompt = """你是一个专业的写作助手，专门帮助用户：
1. 创作各种类型的文档和文章
2. 改进和润色文本
3. 提供写作建议和技巧
4. 协助内容策划和结构化
5. 适应不同的写作风格和场景

请提供高质量、结构化的写作内容和建议。注意语言的流畅性和可读性。"""

            messages = [SystemMessage(content=system_prompt)]

            # 添加对话历史
            if chat_history:
                history_pairs = []
                for i in range(0, len(chat_history), 2):
                    if i + 1 < len(chat_history):
                        history_pairs.append((chat_history[i], chat_history[i + 1]))

                recent_history = history_pairs[-2:] if len(history_pairs) > 2 else history_pairs

                for user_msg, ai_msg in recent_history:
                    messages.append(HumanMessage(content=user_msg))
                    messages.append(AIMessage(content=ai_msg))

            messages.append(HumanMessage(content=message))

            llm = self._get_llm()
            response = await asyncio.to_thread(llm.invoke, messages)

            return f"✍️ {response.content}"

        except Exception as e:
            logger.error(f"生成写作回复失败: {str(e)}")
            return "✍️ 抱歉，我在处理您的写作请求时遇到了技术问题。请稍后重试。"