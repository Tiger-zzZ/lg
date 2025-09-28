"""
文档管理API端点
提供文档上传、处理、搜索等功能
"""
import os
import tempfile
from typing import List, Optional
from pathlib import Path

from fastapi import APIRouter, File, UploadFile, HTTPException, Depends, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.core.logging import logger
from app.models.user import User
from app.models.document import Document, DocumentChunk
from app.core.database import get_db
from app.rag.processor import DocumentProcessor, ProcessingResult
from app.rag.search import SemanticSearch, SearchResult, SearchQuery
from sqlalchemy.orm import Session

# 创建路由器
router = APIRouter(prefix="/documents", tags=["documents"])

# 初始化RAG组件
doc_processor = DocumentProcessor()
search_engine = SemanticSearch()


class DocumentUploadResponse(BaseModel):
    """文档上传响应模型"""
    success: bool
    message: str
    document_id: str
    file_name: str
    chunks_count: int
    processing_time: float


class DocumentInfo(BaseModel):
    """文档信息模型"""
    document_id: str
    file_name: str
    file_path: Optional[str] = None
    created_at: str
    chunks_count: int


class SearchResponse(BaseModel):
    """搜索响应模型"""
    query: str
    total_results: int
    results: List[SearchResult]
    search_time: float


# 支持的文件类型
SUPPORTED_EXTENSIONS = {'.pdf', '.docx', '.txt', '.md'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


# 更简化的测试端点 - 带数据库持久化
@router.post("/test/simple-upload")
async def simple_upload_test(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    简单文档上传 (测试用，无需认证，带数据库持久化)

    Args:
        file: 上传的文件
        db: 数据库会话

    Returns:
        简单的成功响应
    """
    try:
        # 验证文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式。支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # 验证文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)"
            )

        # 生成文档ID
        import uuid
        document_id = str(uuid.uuid4())

        # 简单的块数计算 (每1000字符一个块)
        chunks_count = max(1, len(content.decode('utf-8', errors='ignore')) // 1000)

        # 保存到数据库
        db_document = Document(
            document_id=document_id,
            file_name=file.filename,
            file_size=len(content),
            content_type=file.content_type,
            chunks_count=chunks_count,
            processing_status='completed',
            user_id="00000000-0000-0000-0000-000000000000",  # 测试用户ID
            document_metadata={
                "upload_method": "simple_test",
                "original_filename": file.filename
            }
        )

        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        logger.info(f"简单文档上传成功: {file.filename}, document_id: {document_id}")

        return {
            "success": True,
            "message": "文档上传成功 (简化版)",
            "document_id": document_id,
            "file_name": file.filename,
            "chunks_count": chunks_count,
            "processing_time": 0.1
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"简单文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.get("/test/list")
async def list_documents_test(db: Session = Depends(get_db)):
    """
    列出所有文档 (测试用，无需认证)

    Args:
        db: 数据库会话

    Returns:
        文档列表
    """
    try:
        documents = db.query(Document).all()

        return [
            {
                "document_id": doc.document_id,
                "file_name": doc.file_name,
                "created_at": doc.created_at.isoformat(),
                "chunks_count": doc.chunks_count,
                "processing_status": doc.processing_status,
                "file_size": doc.file_size
            }
            for doc in documents
        ]

    except Exception as e:
        logger.error(f"列出文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.delete("/test/delete/{document_id}")
async def delete_document_test(document_id: str, db: Session = Depends(get_db)):
    """
    删除文档 (测试用，无需认证)

    Args:
        document_id: 文档ID
        db: 数据库会话

    Returns:
        删除结果
    """
    try:
        # 根据document_id查找文档
        document = db.query(Document).filter(Document.document_id == document_id).first()

        if not document:
            raise HTTPException(status_code=404, detail="文档不存在")

        # 删除文档
        db.delete(document)
        db.commit()

        logger.info(f"文档删除成功: {document_id}")

        return {"message": "文档删除成功", "document_id": document_id}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


class DocumentQARequest(BaseModel):
    """文档问答请求模型"""
    question: str


@router.post("/test/qa")
async def document_qa_test(
    request: DocumentQARequest,
    db: Session = Depends(get_db)
):
    """
    文档问答 (测试用，无需认证，简化版)

    Args:
        question = request.question
        db: 数据库会话

    Returns:
        问答结果
    """
    try:
        question = request.question
        # 获取所有文档数量作为上下文
        document_count = db.query(Document).count()

        if document_count == 0:
            return {
                "answer": "目前还没有上传任何文档，请先上传文档后再进行问答。",
                "context": [],
                "source_documents": []
            }

        # 模拟基于文档的回答
        mock_answer = f"""基于您上传的 {document_count} 个文档，我来尝试回答您的问题："{question}"

**回答：** 抱歉，当前是测试模式，我无法访问文档的具体内容来提供准确的回答。在完整版本中，系统会：

1. 搜索相关文档片段
2. 理解问题的上下文
3. 基于文档内容生成准确回答

**建议：** 请确保您的问题与上传的文档内容相关，这样我能提供更有价值的回答。

*注：这是简化的测试版本，完整功能正在开发中。*"""

        return {
            "answer": mock_answer,
            "context": f"基于 {document_count} 个已上传文档",
            "source_documents": [],
            "question": question
        }

    except Exception as e:
        logger.error(f"文档问答失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"问答失败: {str(e)}")
@router.post("/test/upload", response_model=DocumentUploadResponse)
async def upload_document_test(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    上传并处理文档 (测试用，无需认证)

    Args:
        file: 上传的文件
        db: 数据库会话

    Returns:
        DocumentUploadResponse: 上传处理结果
    """
    try:
        # 验证文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式。支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # 验证文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)"
            )

        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension,
            prefix=f"upload_test_"
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # 处理文档
            metadata = {
                "user_id": "00000000-0000-0000-0000-000000000000",  # 测试用户UUID
                "original_filename": file.filename,
                "file_size": len(content),
                "content_type": file.content_type
            }

            result = await doc_processor.process_document(temp_file_path, metadata, db)

            if result.success:
                logger.info(f"文档上传成功 (测试): {file.filename}")
                return DocumentUploadResponse(
                    success=True,
                    message="文档上传并处理成功",
                    document_id=result.document_id,
                    file_name=file.filename,
                    chunks_count=result.chunks_count,
                    processing_time=result.processing_time
                )
            else:
                raise HTTPException(status_code=500, detail=result.message)

        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败 (测试): {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    上传并处理文档

    Args:
        file: 上传的文件
        current_user: 当前用户
        db: 数据库会话

    Returns:
        DocumentUploadResponse: 上传处理结果
    """
    try:
        # 验证文件类型
        file_extension = Path(file.filename).suffix.lower()
        if file_extension not in SUPPORTED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式。支持的格式: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

        # 验证文件大小
        content = await file.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)"
            )

        # 创建临时文件
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=file_extension,
            prefix=f"upload_{current_user.id}_"
        ) as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name

        try:
            # 处理文档
            metadata = {
                "user_id": current_user.id,
                "original_filename": file.filename,
                "file_size": len(content),
                "content_type": file.content_type
            }

            result = await doc_processor.process_document(temp_file_path, metadata, db)

            if result.success:
                logger.info(f"文档上传成功: {file.filename}, 用户: {current_user.id}")
                return DocumentUploadResponse(
                    success=True,
                    message="文档上传并处理成功",
                    document_id=result.document_id,
                    file_name=file.filename,
                    chunks_count=result.chunks_count,
                    processing_time=result.processing_time
                )
            else:
                raise HTTPException(status_code=500, detail=result.message)

        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"文档上传失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档上传失败: {str(e)}")


@router.post("/upload-multiple")
async def upload_multiple_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    批量上传文档

    Args:
        files: 上传的文件列表
        current_user: 当前用户

    Returns:
        List[DocumentUploadResponse]: 批量上传结果
    """
    if len(files) > 10:  # 限制批量上传数量
        raise HTTPException(status_code=400, detail="批量上传最多支持10个文件")

    results = []
    for file in files:
        try:
            result = await upload_document(file, current_user)
            results.append(result)
        except HTTPException as e:
            results.append(DocumentUploadResponse(
                success=False,
                message=str(e.detail),
                document_id="",
                file_name=file.filename,
                chunks_count=0,
                processing_time=0
            ))

    return results


@router.get("/", response_model=List[DocumentInfo])
async def list_documents(
    current_user: User = Depends(get_current_user)
):
    """
    列出用户的所有文档

    Args:
        current_user: 当前用户

    Returns:
        List[DocumentInfo]: 文档列表
    """
    try:
        documents = await doc_processor.list_documents()

        # 过滤当前用户的文档
        user_documents = [
            DocumentInfo(
                document_id=doc["document_id"],
                file_name=doc["file_name"],
                file_path=doc.get("file_path"),
                created_at=doc["created_at"],
                chunks_count=doc["chunks_count"]
            )
            for doc in documents
            # 注意：这里需要根据实际的元数据结构来过滤
        ]

        return user_documents

    except Exception as e:
        logger.error(f"列出文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/list", response_model=List[DocumentInfo])
async def list_documents_alias():
    """
    列出所有文档 (兼容前端，开发期间无需认证)

    Returns:
        List[DocumentInfo]: 文档列表
    """
    try:
        # 在开发环境中，使用简单的测试用户
        from app.core.database import get_db
        from app.models.document import Document

        # 获取数据库会话
        db = next(get_db())

        try:
            documents = db.query(Document).all()

            return [
                DocumentInfo(
                    document_id=doc.document_id,
                    file_name=doc.file_name,
                    created_at=doc.created_at.isoformat(),
                    chunks_count=doc.chunks_count,
                    file_path=doc.file_path
                )
                for doc in documents
            ]
        finally:
            db.close()

    except Exception as e:
        logger.error(f"列出文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


# 开发环境的无认证列表端点 (兼容前端开发)
@router.get("/list/dev")
async def list_documents_dev(db: Session = Depends(get_db)):
    """
    列出所有文档 (开发用，无需认证)

    Args:
        db: 数据库会话

    Returns:
        List[DocumentInfo]: 文档列表
    """
    try:
        documents = db.query(Document).all()

        return [
            {
                "document_id": doc.document_id,
                "file_name": doc.file_name,
                "created_at": doc.created_at.isoformat(),
                "chunks_count": doc.chunks_count,
                "processing_status": doc.processing_status,
                "file_size": doc.file_size
            }
            for doc in documents
        ]
    except Exception as e:
        logger.error(f"列出文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档列表失败: {str(e)}")


@router.get("/{document_id}", response_model=DocumentInfo)
async def get_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    获取指定文档信息

    Args:
        document_id: 文档ID
        current_user: 当前用户

    Returns:
        DocumentInfo: 文档信息
    """
    try:
        doc_info = await doc_processor.get_document_info(document_id)

        if not doc_info:
            raise HTTPException(status_code=404, detail="文档不存在")

        return DocumentInfo(
            document_id=doc_info["document_id"],
            file_name=doc_info["file_name"],
            file_path=doc_info.get("file_path"),
            created_at=doc_info["created_at"],
            chunks_count=doc_info["chunks_count"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文档信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取文档信息失败: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str,
    current_user: User = Depends(get_current_user)
):
    """
    删除指定文档

    Args:
        document_id: 文档ID
        current_user: 当前用户

    Returns:
        JSONResponse: 删除结果
    """
    try:
        success = await doc_processor.delete_document(document_id)

        if success:
            logger.info(f"文档删除成功: {document_id}, 用户: {current_user.id}")
            return JSONResponse(
                content={"message": "文档删除成功", "document_id": document_id}
            )
        else:
            raise HTTPException(status_code=404, detail="文档不存在或删除失败")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除文档失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"删除文档失败: {str(e)}")


@router.post("/search", response_model=SearchResponse)
async def search_documents(
    search_query: SearchQuery,
    current_user: User = Depends(get_current_user)
):
    """
    搜索文档内容

    Args:
        search_query: 搜索查询
        current_user: 当前用户

    Returns:
        SearchResponse: 搜索结果
    """
    import time
    start_time = time.time()

    try:
        # 添加用户过滤
        filter_metadata = search_query.filter_metadata or {}
        filter_metadata["user_id"] = current_user.id

        results = await search_engine.search(
            query=search_query.query,
            top_k=search_query.top_k,
            filter_metadata=filter_metadata,
            min_score=search_query.min_score
        )

        search_time = time.time() - start_time

        logger.info(f"文档搜索完成: 用户={current_user.id}, 查询='{search_query.query}', 结果数={len(results)}")

        return SearchResponse(
            query=search_query.query,
            total_results=len(results),
            results=results,
            search_time=search_time
        )

    except Exception as e:
        logger.error(f"文档搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@router.post("/hybrid-search", response_model=SearchResponse)
async def hybrid_search_documents(
    query: str,
    top_k: int = Query(5, ge=1, le=50),
    keyword_weight: float = Query(0.3, ge=0.0, le=1.0),
    semantic_weight: float = Query(0.7, ge=0.0, le=1.0),
    current_user: User = Depends(get_current_user)
):
    """
    混合搜索文档内容 (语义 + 关键词)

    Args:
        query: 搜索查询
        top_k: 返回结果数量
        keyword_weight: 关键词搜索权重
        semantic_weight: 语义搜索权重
        current_user: 当前用户

    Returns:
        SearchResponse: 搜索结果
    """
    import time
    start_time = time.time()

    try:
        # 添加用户过滤
        filter_metadata = {"user_id": current_user.id}

        results = await search_engine.hybrid_search(
            query=query,
            top_k=top_k,
            keyword_weight=keyword_weight,
            semantic_weight=semantic_weight,
            filter_metadata=filter_metadata
        )

        search_time = time.time() - start_time

        logger.info(f"混合搜索完成: 用户={current_user.id}, 查询='{query}', 结果数={len(results)}")

        return SearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            search_time=search_time
        )

    except Exception as e:
        logger.error(f"混合搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"混合搜索失败: {str(e)}")


@router.get("/{document_id}/search", response_model=SearchResponse)
async def search_in_document(
    document_id: str,
    query: str,
    top_k: int = Query(5, ge=1, le=50),
    current_user: User = Depends(get_current_user)
):
    """
    在指定文档内搜索

    Args:
        document_id: 文档ID
        query: 搜索查询
        top_k: 返回结果数量
        current_user: 当前用户

    Returns:
        SearchResponse: 搜索结果
    """
    import time
    start_time = time.time()

    try:
        results = await search_engine.search_by_document(
            document_id=document_id,
            query=query,
            top_k=top_k
        )

        search_time = time.time() - start_time

        return SearchResponse(
            query=query,
            total_results=len(results),
            results=results,
            search_time=search_time
        )

    except Exception as e:
        logger.error(f"文档内搜索失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"文档内搜索失败: {str(e)}")


@router.get("/stats/overview")
async def get_search_statistics(
    current_user: User = Depends(get_current_user)
):
    """
    获取搜索统计信息

    Args:
        current_user: 当前用户

    Returns:
        Dict: 统计信息
    """
    try:
        stats = await search_engine.get_search_statistics()
        return stats

    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")


@router.get("/health")
async def documents_health_check():
    """
    文档服务健康检查

    Returns:
        Dict: 健康状态
    """
    try:
        # 测试ChromaDB连接
        stats = await search_engine.get_search_statistics()

        return {
            "status": "healthy",
            "chroma_connected": True,
            "total_documents": stats.get("total_documents", 0),
            "total_chunks": stats.get("total_chunks", 0)
        }

    except Exception as e:
        logger.error(f"文档服务健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "chroma_connected": False,
            "error": str(e)
        }