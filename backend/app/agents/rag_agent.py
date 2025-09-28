"""
RAG Agent - 基于检索增强生成的智能代理
集成文档知识库，提供基于上下文的智能回答
"""
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage

from ..base import BaseAgent, AgentState
from ...rag.search import SemanticSearch, SearchResult
from ...core.config import settings
from ...core.logger import logger


class RAGAgent(BaseAgent):
    """RAG智能代理"""

    def __init__(self, name: str = "RAG Agent"):
        super().__init__(name)
        self.search_engine = SemanticSearch()
        self.llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            model="gpt-3.5-turbo",
            temperature=0.7,
            max_tokens=1000
        )
        self.max_context_length = 4000  # 最大上下文长度
        self.search_top_k = 5  # 检索文档数量

    async def _process(self, state: AgentState) -> AgentState:
        """处理用户查询，集成RAG检索"""
        try:
            if not state.messages:
                raise ValueError("没有消息需要处理")

            # 获取最新用户消息
            latest_message = state.messages[-1]
            logger.info(f"RAG Agent 处理查询: {latest_message[:100]}...")

            # 1. 检索相关文档
            search_results = await self._retrieve_documents(
                query=latest_message,
                user_id=state.metadata.get("user_id")
            )

            # 2. 构建增强上下文
            context = self._build_context(search_results)

            # 3. 生成回答
            response = await self._generate_response(
                query=latest_message,
                context=context,
                chat_history=state.messages[:-1]
            )

            # 4. 更新状态
            state.messages.append(response)
            state.metadata["rag_sources"] = [
                {
                    "document_id": result.document_id,
                    "chunk_index": result.chunk_index,
                    "score": result.score,
                    "content_preview": result.content[:100]
                }
                for result in search_results
            ]
            state.metadata["context_length"] = len(context)
            state.result = response

            logger.info(f"RAG Agent 处理完成，使用了 {len(search_results)} 个文档片段")

            return state

        except Exception as e:
            logger.error(f"RAG Agent 处理失败: {str(e)}")
            error_message = "抱歉，在处理您的查询时遇到了问题。请稍后重试。"

            state.messages.append(error_message)
            state.result = error_message
            state.status = "error"
            state.error = str(e)

            return state

    async def _retrieve_documents(
        self,
        query: str,
        user_id: Optional[str] = None
    ) -> List[SearchResult]:
        """检索相关文档"""
        try:
            # 构建过滤条件
            filter_metadata = {}
            if user_id:
                filter_metadata["user_id"] = user_id

            # 执行混合搜索 (语义 + 关键词)
            search_results = await self.search_engine.hybrid_search(
                query=query,
                top_k=self.search_top_k,
                keyword_weight=0.3,
                semantic_weight=0.7,
                filter_metadata=filter_metadata
            )

            logger.info(f"检索到 {len(search_results)} 个相关文档片段")
            return search_results

        except Exception as e:
            logger.error(f"文档检索失败: {str(e)}")
            return []

    def _build_context(self, search_results: List[SearchResult]) -> str:
        """构建检索增强上下文"""
        if not search_results:
            return "没有找到相关的文档信息。"

        context_parts = []
        current_length = 0

        for i, result in enumerate(search_results):
            # 格式化文档片段
            doc_part = f"""
文档片段 {i + 1} (相似度: {result.score:.2f}):
{result.content}

---
"""
            # 检查长度限制
            if current_length + len(doc_part) > self.max_context_length:
                break

            context_parts.append(doc_part)
            current_length += len(doc_part)

        context = "以下是相关的文档信息：\n\n" + "\n".join(context_parts)
        return context

    async def _generate_response(
        self,
        query: str,
        context: str,
        chat_history: List[str]
    ) -> str:
        """基于上下文生成回答"""
        try:
            # 构建系统提示
            system_prompt = """你是一个智能助手，专门回答基于提供文档的问题。请遵循以下规则：

1. 优先使用提供的文档信息回答问题
2. 如果文档中没有相关信息，请明确说明
3. 提供准确、有用的回答
4. 保持回答的简洁性和可读性
5. 如果需要，可以引用文档中的具体内容

请基于提供的文档上下文回答用户的问题。"""

            # 构建消息序列
            messages = [
                SystemMessage(content=system_prompt)
            ]

            # 添加历史对话 (限制长度)
            if chat_history:
                history_text = "\n".join(chat_history[-6:])  # 最近3轮对话
                messages.append(
                    HumanMessage(content=f"历史对话：\n{history_text}")
                )

            # 添加当前查询和上下文
            user_message = f"""
用户问题: {query}

相关文档信息:
{context}

请基于上述文档信息回答用户的问题。"""

            messages.append(HumanMessage(content=user_message))

            # 调用LLM生成回答
            response = await asyncio.to_thread(
                self.llm.invoke, messages
            )

            return response.content

        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            return "抱歉，我在生成回答时遇到了问题。请稍后重试。"

    async def search_documents(
        self,
        query: str,
        top_k: int = 5,
        user_id: Optional[str] = None
    ) -> List[SearchResult]:
        """直接搜索文档 (供外部调用)"""
        filter_metadata = {}
        if user_id:
            filter_metadata["user_id"] = user_id

        return await self.search_engine.search(
            query=query,
            top_k=top_k,
            filter_metadata=filter_metadata
        )

    async def get_document_summary(
        self,
        document_id: str,
        user_id: Optional[str] = None
    ) -> str:
        """获取文档摘要"""
        try:
            # 搜索文档的所有片段
            filter_metadata = {"document_id": document_id}
            if user_id:
                filter_metadata["user_id"] = user_id

            results = await self.search_engine.search(
                query="文档内容摘要",
                top_k=10,
                filter_metadata=filter_metadata
            )

            if not results:
                return "未找到指定文档。"

            # 构建文档内容
            content_parts = []
            for result in results:
                content_parts.append(result.content)

            full_content = "\n\n".join(content_parts)

            # 生成摘要
            summary_prompt = f"""
请为以下文档内容生成一个简洁的摘要：

{full_content[:3000]}  # 限制长度

摘要要求：
1. 概括主要内容和关键点
2. 保持简洁明了
3. 突出重要信息
"""

            messages = [
                SystemMessage(content="你是一个文档摘要助手，能够生成准确简洁的文档摘要。"),
                HumanMessage(content=summary_prompt)
            ]

            response = await asyncio.to_thread(
                self.llm.invoke, messages
            )

            return response.content

        except Exception as e:
            logger.error(f"生成文档摘要失败: {str(e)}")
            return "生成文档摘要时遇到问题。"

    def get_agent_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "name": self.name,
            "type": "rag",
            "description": "基于检索增强生成的智能问答代理，能够利用上传的文档知识库回答问题",
            "capabilities": [
                "文档问答",
                "语义搜索",
                "上下文理解",
                "知识检索",
                "文档摘要"
            ],
            "config": {
                "search_top_k": self.search_top_k,
                "max_context_length": self.max_context_length,
                "model": "gpt-3.5-turbo"
            }
        }