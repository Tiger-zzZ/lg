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
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import (
    PyPDFLoader,
    Docx2txtLoader,
    TextLoader,
    UnstructuredMarkdownLoader
)
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import logger
from app.core.database import get_db
from app.models.document import Document, DocumentChunk as DBDocumentChunk
from sqlalchemy.orm import Session


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
        self._embeddings = None
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""]
        )

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

    async def process_document(
        self,
        file_path: str,
        metadata: Optional[Dict] = None,
        db: Optional[Session] = None
    ) -> ProcessingResult:
        """
        处理单个文档

        Args:
            file_path: 文档路径
            metadata: 额外的元数据
            db: 数据库会话（可选）

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

            # 保存到数据库（如果提供了数据库会话）
            if db and metadata:
                await self._save_to_database(
                    db, document_id, file_path, doc_chunks, metadata
                )

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
            '.md': TextLoader  # 暂时使用TextLoader代替UnstructuredMarkdownLoader
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
        embeddings_model = self._get_embeddings()
        embeddings = await asyncio.to_thread(
            embeddings_model.embed_documents, texts
        )

        # 准备存储数据
        ids = [chunk.id for chunk in chunks]
        # 确保metadata中的所有值都是ChromaDB支持的类型
        metadatas = []
        for chunk in chunks:
            metadata = {}
            for key, value in chunk.metadata.items():
                # 将UUID等对象转换为字符串
                if hasattr(value, '__str__') and not isinstance(value, (str, int, float, bool, type(None))):
                    metadata[key] = str(value)
                else:
                    metadata[key] = value
            metadatas.append(metadata)
        documents = [chunk.content for chunk in chunks]

        # 存储到ChromaDB
        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents
        )

        logger.info(f"成功存储 {len(chunks)} 个文档块到向量数据库")

    async def _save_to_database(
        self,
        db: Session,
        document_id: str,
        file_path: str,
        chunks: List[DocumentChunk],
        metadata: Dict
    ):
        """保存文档信息到数据库"""
        try:
            from pathlib import Path
            import os

            # 创建文档记录
            file_stats = os.stat(file_path) if os.path.exists(file_path) else None

            db_document = Document(
                document_id=document_id,
                file_name=metadata.get("original_filename", Path(file_path).name),
                file_path=file_path,
                file_size=metadata.get("file_size", file_stats.st_size if file_stats else 0),
                content_type=metadata.get("content_type", ""),
                chunks_count=len(chunks),
                processing_status='completed',
                user_id=metadata.get("user_id", "00000000-0000-0000-0000-000000000000"),
                document_metadata={
                    "processing_method": "full_rag",
                    "embedding_model": settings.EMBEDDING_MODEL,
                    **{k: v for k, v in metadata.items() if k not in ["user_id"]}
                },
                processed_at=datetime.utcnow()
            )

            db.add(db_document)
            db.flush()  # 获取数据库生成的ID

            # 创建文档块记录
            for chunk in chunks:
                db_chunk = DBDocumentChunk(
                    document_id=db_document.id,
                    chunk_index=chunk.metadata.get("chunk_index", 0),
                    content=chunk.content,
                    content_preview=chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    chroma_id=chunk.id,
                    chunk_metadata=chunk.metadata
                )
                db.add(db_chunk)

            db.commit()
            logger.info(f"成功保存文档到数据库: {document_id}, 用户: {metadata.get('user_id')}")

        except Exception as e:
            db.rollback()
            logger.error(f"保存文档到数据库失败: {document_id}, 错误: {str(e)}")
            raise

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