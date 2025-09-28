"""
语义搜索模块
提供基于向量相似度和混合搜索功能
"""
import asyncio
from typing import List, Dict, Optional, Union
from datetime import datetime

import chromadb
from langchain_openai import OpenAIEmbeddings
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger


class SearchResult(BaseModel):
    """搜索结果数据模型"""
    id: str
    content: str
    metadata: Dict
    score: float
    document_id: str
    chunk_index: int


class SearchQuery(BaseModel):
    """搜索查询模型"""
    query: str
    top_k: int = 5
    filter_metadata: Optional[Dict] = None
    min_score: Optional[float] = None


class SemanticSearch:
    """语义搜索引擎"""

    def __init__(self):
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        self.collection = self.client.get_or_create_collection("documents")
        self._embeddings = None

    def _get_embeddings(self):
        """延迟初始化 OpenAI Embeddings"""
        if self._embeddings is None:
            if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY in ['', 'EMPTY', 'sk-your-openai-api-key-here']:
                raise ValueError(
                    "OpenAI API 密钥未配置。请在 .env 文件中设置有效的 OPENAI_API_KEY。"
                )
            self._embeddings = OpenAIEmbeddings(
                openai_api_key=settings.OPENAI_API_KEY,
                openai_api_base=settings.OPENAI_BASE_URL,
                model=settings.EMBEDDING_MODEL
            )
        return self._embeddings

    async def search(
        self,
        query: str,
        top_k: int = 5,
        filter_metadata: Optional[Dict] = None,
        min_score: Optional[float] = None
    ) -> List[SearchResult]:
        """
        执行语义搜索

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件
            min_score: 最小相似度分数

        Returns:
            List[SearchResult]: 搜索结果列表
        """
        try:
            # 生成查询向量
            embeddings_model = self._get_embeddings()
            query_embedding = await asyncio.to_thread(
                embeddings_model.embed_query, query
            )

            # 执行向量搜索
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": top_k
            }

            # 添加过滤条件
            if filter_metadata:
                search_params["where"] = filter_metadata

            results = self.collection.query(**search_params)

            # 转换为SearchResult对象
            search_results = []
            for i in range(len(results['ids'][0])):
                # 计算相似度分数 (距离越小，相似度越高)
                distance = results['distances'][0][i]
                score = max(0, 1 - distance)

                # 应用最小分数过滤
                if min_score and score < min_score:
                    continue

                metadata = results['metadatas'][0][i]
                result = SearchResult(
                    id=results['ids'][0][i],
                    content=results['documents'][0][i],
                    metadata=metadata,
                    score=score,
                    document_id=metadata.get('document_id', ''),
                    chunk_index=metadata.get('chunk_index', 0)
                )
                search_results.append(result)

            logger.info(f"语义搜索完成: 查询='{query}', 结果数={len(search_results)}")
            return search_results

        except Exception as e:
            logger.error(f"语义搜索失败: {str(e)}")
            return []

    async def hybrid_search(
        self,
        query: str,
        top_k: int = 5,
        keyword_weight: float = 0.3,
        semantic_weight: float = 0.7,
        filter_metadata: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        执行混合搜索 (语义搜索 + 关键词搜索)

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            keyword_weight: 关键词搜索权重
            semantic_weight: 语义搜索权重
            filter_metadata: 元数据过滤条件

        Returns:
            List[SearchResult]: 混合搜索结果
        """
        try:
            # 执行语义搜索
            semantic_results = await self.search(
                query, top_k * 2, filter_metadata
            )

            # 执行关键词搜索 (基于文本匹配)
            keyword_results = await self._keyword_search(
                query, top_k * 2, filter_metadata
            )

            # 合并和重新评分
            combined_results = self._combine_search_results(
                semantic_results,
                keyword_results,
                semantic_weight,
                keyword_weight
            )

            # 返回前top_k个结果
            return combined_results[:top_k]

        except Exception as e:
            logger.error(f"混合搜索失败: {str(e)}")
            return []

    async def _keyword_search(
        self,
        query: str,
        top_k: int,
        filter_metadata: Optional[Dict] = None
    ) -> List[SearchResult]:
        """
        关键词搜索 (基于文本包含)

        Args:
            query: 搜索查询
            top_k: 返回结果数量
            filter_metadata: 元数据过滤条件

        Returns:
            List[SearchResult]: 关键词搜索结果
        """
        try:
            # 获取所有文档
            search_params = {}
            if filter_metadata:
                search_params["where"] = filter_metadata

            results = self.collection.get(**search_params)

            # 关键词匹配和评分
            keyword_results = []
            query_lower = query.lower()
            query_words = set(query_lower.split())

            for i in range(len(results['ids'])):
                content = results['documents'][i].lower()
                metadata = results['metadatas'][i]

                # 计算关键词匹配分数
                content_words = set(content.split())
                intersection = query_words.intersection(content_words)

                if intersection:
                    # 基于匹配词数和位置的简单评分
                    score = len(intersection) / len(query_words)

                    # 精确短语匹配加分
                    if query_lower in content:
                        score += 0.3

                    result = SearchResult(
                        id=results['ids'][i],
                        content=results['documents'][i],
                        metadata=metadata,
                        score=min(score, 1.0),
                        document_id=metadata.get('document_id', ''),
                        chunk_index=metadata.get('chunk_index', 0)
                    )
                    keyword_results.append(result)

            # 按分数排序
            keyword_results.sort(key=lambda x: x.score, reverse=True)
            return keyword_results[:top_k]

        except Exception as e:
            logger.error(f"关键词搜索失败: {str(e)}")
            return []

    def _combine_search_results(
        self,
        semantic_results: List[SearchResult],
        keyword_results: List[SearchResult],
        semantic_weight: float,
        keyword_weight: float
    ) -> List[SearchResult]:
        """
        合并语义搜索和关键词搜索结果

        Args:
            semantic_results: 语义搜索结果
            keyword_results: 关键词搜索结果
            semantic_weight: 语义搜索权重
            keyword_weight: 关键词搜索权重

        Returns:
            List[SearchResult]: 合并后的结果
        """
        # 创建结果字典，以ID为键
        combined = {}

        # 添加语义搜索结果
        for result in semantic_results:
            combined[result.id] = SearchResult(
                id=result.id,
                content=result.content,
                metadata=result.metadata,
                score=result.score * semantic_weight,
                document_id=result.document_id,
                chunk_index=result.chunk_index
            )

        # 添加或合并关键词搜索结果
        for result in keyword_results:
            if result.id in combined:
                # 合并分数
                combined[result.id].score += result.score * keyword_weight
            else:
                # 新结果
                combined[result.id] = SearchResult(
                    id=result.id,
                    content=result.content,
                    metadata=result.metadata,
                    score=result.score * keyword_weight,
                    document_id=result.document_id,
                    chunk_index=result.chunk_index
                )

        # 转换为列表并排序
        final_results = list(combined.values())
        final_results.sort(key=lambda x: x.score, reverse=True)

        return final_results

    async def search_by_document(
        self,
        document_id: str,
        query: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        在指定文档内搜索

        Args:
            document_id: 文档ID
            query: 搜索查询
            top_k: 返回结果数量

        Returns:
            List[SearchResult]: 搜索结果
        """
        filter_metadata = {"document_id": document_id}
        return await self.search(query, top_k, filter_metadata)

    async def get_similar_chunks(
        self,
        chunk_id: str,
        top_k: int = 5
    ) -> List[SearchResult]:
        """
        获取与指定块相似的其他块

        Args:
            chunk_id: 块ID
            top_k: 返回结果数量

        Returns:
            List[SearchResult]: 相似块列表
        """
        try:
            # 获取指定块的内容
            chunk_result = self.collection.get(ids=[chunk_id])
            if not chunk_result['documents']:
                return []

            chunk_content = chunk_result['documents'][0]

            # 使用块内容作为查询进行相似搜索
            results = await self.search(chunk_content, top_k + 1)

            # 排除自身
            return [r for r in results if r.id != chunk_id][:top_k]

        except Exception as e:
            logger.error(f"获取相似块失败: {str(e)}")
            return []

    async def get_search_statistics(self) -> Dict:
        """
        获取搜索统计信息

        Returns:
            Dict: 统计信息
        """
        try:
            # 获取所有文档
            all_results = self.collection.get()
            total_chunks = len(all_results['ids'])

            # 统计文档数量
            document_ids = set()
            for metadata in all_results['metadatas']:
                doc_id = metadata.get('document_id')
                if doc_id:
                    document_ids.add(doc_id)

            return {
                "total_documents": len(document_ids),
                "total_chunks": total_chunks,
                "average_chunks_per_document": total_chunks / len(document_ids) if document_ids else 0,
                "collection_name": self.collection.name
            }

        except Exception as e:
            logger.error(f"获取搜索统计失败: {str(e)}")
            return {
                "total_documents": 0,
                "total_chunks": 0,
                "average_chunks_per_document": 0,
                "collection_name": "documents"
            }