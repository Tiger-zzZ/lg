"""
文档处理器模块
处理各种格式的文档，进行分块和向量化
"""
import os
import hashlib
from typing import List, Dict, Optional, Union
from pathlib import Path
import asyncio
from datetime import datetime

import chromadb
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from pydantic import BaseModel

from app.core.config import settings
from app.core.logger import logger


class DocumentChunk(BaseModel):
    """文档块数据模型"""
    id: str
    content: str
    metadata: Dict
    embedding: Optional[List[float]] = None


class ProcessingResult(BaseModel):
    """处理结果模型"""
    success: bool
    document_id: str
    chunks_count: int
    message: str
    processing_time: float


class DocumentProcessor:
    """文档处理器"""

    def __init__(self):
        self.client = chromadb.HttpClient(
            host=settings.CHROMA_HOST,
            port=settings.CHROMA_PORT
        )
        self.collection = self.client.get_or_create_collection("documents")
        self.embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

    async def process_document(
        self,
        file_path: str,
        metadata: Optional[Dict] = None
    ) -> ProcessingResult:
        """
        处理单个文档

        Args:
            file_path: 文档路径
            metadata: 额外的元数据

        Returns:
            ProcessingResult: 处理结果
        """
        start_time = datetime.now()

        try:
            # 生成文档ID
            document_id = self._generate_document_id(file_path)

            # 加载文档
            documents = await self._load_document(file_path)
            if not documents:
                return ProcessingResult(
                    success=False,
                    document_id=document_id,
                    chunks_count=0,
                    message="无法加载文档",
                    processing_time=0
                )

            # 分块
            chunks = self._split_documents(documents)

            # 创建文档块
            doc_chunks = []
            for i, chunk in enumerate(chunks):
                chunk_metadata = {
                    "document_id": document_id,
                    "chunk_index": i,
                    "file_path": file_path,
                    "file_name": Path(file_path).name,
                    "created_at": datetime.utcnow().isoformat(),
                    **(metadata or {})
                }

                doc_chunk = DocumentChunk(
                    id=f"{document_id}_{i}",
                    content=chunk.page_content,
                    metadata=chunk_metadata
                )
                doc_chunks.append(doc_chunk)

            # 向量化并存储
            await self._vectorize_and_store(doc_chunks)

            processing_time = (datetime.now() - start_time).total_seconds()

            logger.info(f"文档处理完成: {file_path}, 块数: {len(doc_chunks)}, 耗时: {processing_time:.2f}s")

            return ProcessingResult(
                success=True,
                document_id=document_id,
                chunks_count=len(doc_chunks),
                message="处理成功",
                processing_time=processing_time
            )

        except Exception as e:
            processing_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"文档处理失败: {file_path}, 错误: {str(e)}")

            return ProcessingResult(
                success=False,
                document_id=document_id if 'document_id' in locals() else "",
                chunks_count=0,
                message=f"处理失败: {str(e)}",
                processing_time=processing_time
            )

    async def process_multiple_documents(
        self,
        file_paths: List[str],
        metadata: Optional[Dict] = None
    ) -> List[ProcessingResult]:
        """
        批量处理多个文档

        Args:
            file_paths: 文档路径列表
            metadata: 额外的元数据

        Returns:
            List[ProcessingResult]: 处理结果列表
        """
        tasks = [
            self.process_document(file_path, metadata)
            for file_path in file_paths
        ]
        return await asyncio.gather(*tasks)

    async def _load_document(self, file_path: str):
        """根据文件类型加载文档"""
        file_extension = Path(file_path).suffix.lower()

        loaders = {
            '.pdf': PyPDFLoader,
            '.docx': Docx2txtLoader,
            '.txt': TextLoader,
            '.md': UnstructuredMarkdownLoader
        }

        loader_class = loaders.get(file_extension)
        if not loader_class:
            raise ValueError(f"不支持的文件格式: {file_extension}")

        loader = loader_class(file_path)
        return loader.load()

    def _split_documents(self, documents):
        """分割文档为块"""
        return self.text_splitter.split_documents(documents)

    async def _vectorize_and_store(self, chunks: List[DocumentChunk]):
        """向量化文档块并存储到ChromaDB"""
        if not chunks:
            return

        # 提取文本内容
        texts = [chunk.content for chunk in chunks]

        # 生成嵌入向量
        embeddings = await asyncio.to_thread(
            self.embeddings.embed_documents, texts
        )

        # 准备存储数据
        ids = [chunk.id for chunk in chunks]
        metadatas = [chunk.metadata for chunk in chunks]
        documents = [chunk.content for chunk in chunks]

        # 存储到ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

        logger.info(f"成功存储 {len(chunks)} 个文档块到向量数据库")

    def _generate_document_id(self, file_path: str) -> str:
        """生成文档唯一ID"""
        # 使用文件路径和修改时间生成哈希
        stat = os.stat(file_path)
        content = f"{file_path}_{stat.st_mtime}_{stat.st_size}"
        return hashlib.md5(content.encode()).hexdigest()

    async def delete_document(self, document_id: str) -> bool:
        """
        删除文档及其所有块

        Args:
            document_id: 文档ID

        Returns:
            bool: 删除是否成功
        """
        try:
            # 查询所有属于该文档的块
            results = self.collection.get(
                where={"document_id": document_id}
            )

            if results['ids']:
                # 删除所有块
                self.collection.delete(ids=results['ids'])
                logger.info(f"成功删除文档: {document_id}, 块数: {len(results['ids'])}")
                return True
            else:
                logger.warning(f"未找到文档: {document_id}")
                return False

        except Exception as e:
            logger.error(f"删除文档失败: {document_id}, 错误: {str(e)}")
            return False

    async def get_document_info(self, document_id: str) -> Optional[Dict]:
        """
        获取文档信息

        Args:
            document_id: 文档ID

        Returns:
            Dict: 文档信息
        """
        try:
            results = self.collection.get(
                where={"document_id": document_id},
                limit=1
            )

            if results['metadatas']:
                metadata = results['metadatas'][0]
                return {
                    "document_id": document_id,
                    "file_name": metadata.get("file_name"),
                    "file_path": metadata.get("file_path"),
                    "created_at": metadata.get("created_at"),
                    "chunks_count": len(self.collection.get(
                        where={"document_id": document_id}
                    )['ids'])
                }
            return None

        except Exception as e:
            logger.error(f"获取文档信息失败: {document_id}, 错误: {str(e)}")
            return None

    async def list_documents(self) -> List[Dict]:
        """
        列出所有文档

        Returns:
            List[Dict]: 文档列表
        """
        try:
            # 获取所有独特的document_id
            results = self.collection.get()

            documents = {}
            for metadata in results['metadatas']:
                doc_id = metadata.get('document_id')
                if doc_id and doc_id not in documents:
                    documents[doc_id] = {
                        "document_id": doc_id,
                        "file_name": metadata.get("file_name"),
                        "file_path": metadata.get("file_path"),
                        "created_at": metadata.get("created_at"),
                        "chunks_count": 1
                    }
                elif doc_id:
                    documents[doc_id]["chunks_count"] += 1

            return list(documents.values())

        except Exception as e:
            logger.error(f"列出文档失败: {str(e)}")
            return []