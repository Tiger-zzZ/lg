"""
文档模型
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, Boolean, BigInteger, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.core.database import Base


class Document(Base):
    """文档表"""
    __tablename__ = "documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(String(255), unique=True, nullable=False, index=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    content_type = Column(String(100), nullable=True)
    chunks_count = Column(Integer, default=0)
    processing_status = Column(String(50), default='pending')  # pending, processing, completed, failed
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)

    # 元数据
    document_metadata = Column(JSON, nullable=True, default={})

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    processed_at = Column(DateTime(timezone=True), nullable=True)

    # 关系
    user = relationship("User", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Document(id={self.id}, file_name='{self.file_name}', user_id={self.user_id})>"


class DocumentChunk(Base):
    """文档块表"""
    __tablename__ = "document_chunks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey('documents.id'), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_preview = Column(Text, nullable=True)  # 内容预览，用于搜索结果显示

    # ChromaDB相关
    chroma_id = Column(String(255), nullable=True, index=True)

    # 元数据
    chunk_metadata = Column(JSON, nullable=True, default={})

    # 时间戳
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 关系
    document = relationship("Document", back_populates="chunks")

    def __repr__(self):
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"