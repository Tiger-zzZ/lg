"""
聊天和问答API端点
提供对话、文档问答、搜索等功能
"""
import asyncio
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.models.user import User
from app.agents.manager import agent_manager
from app.core.logging import logger

# 创建路由器
router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """聊天消息模型"""
    role: str  # "user" or "assistant"
    content: str
    timestamp: Optional[datetime] = None


class ChatRequest(BaseModel):
    """聊天请求模型"""
    message: str
    conversation_history: Optional[List[ChatMessage]] = None
    agent_type: str = "chat"  # "chat", "rag", "search"


class ChatResponse(BaseModel):
    """聊天响应模型"""
    message: str
    agent_type: str
    response_time: float
    metadata: Optional[dict] = None


class DocumentQARequest(BaseModel):
    """文档问答请求模型"""
    question: str
    document_ids: Optional[List[str]] = None
    conversation_history: Optional[List[ChatMessage]] = None


class SearchRequest(BaseModel):
    """搜索请求模型"""
    query: str
    max_results: int = 5


# 临时测试端点 - 无需认证
@router.post("/test/message", response_model=ChatResponse)
async def send_message_test(request: ChatRequest):
    """
    发送聊天消息 (测试用，无需认证)

    Args:
        request: 聊天请求

    Returns:
        ChatResponse: 聊天响应
    """
    import time
    start_time = time.time()

    try:
        # 创建Agent
        agent = agent_manager.create_agent(request.agent_type)

        # 构建消息历史
        messages = []
        if request.conversation_history:
            for msg in request.conversation_history:
                messages.append(msg.content)
        messages.append(request.message)

        # 构建状态
        state = {
            "messages": messages,
            "metadata": {
                "user_id": "test_user",
                "agent_type": request.agent_type
            },
            "status": "pending",
            "result": None,
            "error": None
        }

        # 执行Agent
        result_state = await agent.execute(messages, state["metadata"])

        response_time = time.time() - start_time

        logger.info(f"聊天处理完成 (测试): agent_type={request.agent_type}, 耗时={response_time:.2f}s")

        return ChatResponse(
            message=result_state["result"],
            agent_type=request.agent_type,
            response_time=response_time,
            metadata=result_state["metadata"]
        )

    except Exception as e:
        logger.error(f"聊天处理失败 (测试): {str(e)}")
        response_time = time.time() - start_time

        return ChatResponse(
            message=f"抱歉，处理您的消息时遇到问题：{str(e)}",
            agent_type=request.agent_type,
            response_time=response_time,
            metadata={"error": str(e)}
        )


@router.post("/message", response_model=ChatResponse)
async def send_message(
    request: ChatRequest,
    current_user: User = Depends(get_current_user)
):
    """
    发送聊天消息

    Args:
        request: 聊天请求
        current_user: 当前用户

    Returns:
        ChatResponse: 聊天响应
    """
    import time
    start_time = time.time()

    try:
        # 创建Agent
        agent = agent_manager.create_agent(request.agent_type)

        # 构建消息历史
        messages = []
        if request.conversation_history:
            for msg in request.conversation_history:
                messages.append(msg.content)
        messages.append(request.message)

        # 构建状态
        state = {
            "messages": messages,
            "metadata": {
                "user_id": str(current_user.id),
                "agent_type": request.agent_type
            },
            "status": "pending",
            "result": None,
            "error": None
        }

        # 执行Agent
        result_state = await agent.execute(messages, state["metadata"])

        response_time = time.time() - start_time

        logger.info(f"聊天处理完成: user_id={current_user.id}, agent_type={request.agent_type}, 耗时={response_time:.2f}s")

        return ChatResponse(
            message=result_state["result"],
            agent_type=request.agent_type,
            response_time=response_time,
            metadata=result_state["metadata"]
        )

    except Exception as e:
        logger.error(f"聊天处理失败: user_id={current_user.id}, error={str(e)}")
        response_time = time.time() - start_time

        return ChatResponse(
            message=f"抱歉，处理您的消息时遇到问题：{str(e)}",
            agent_type=request.agent_type,
            response_time=response_time,
            metadata={"error": str(e)}
        )


@router.post("/qa", response_model=ChatResponse)
async def document_qa(
    request: DocumentQARequest,
    current_user: User = Depends(get_current_user)
):
    """
    文档问答

    Args:
        request: 问答请求
        current_user: 当前用户

    Returns:
        ChatResponse: 问答响应
    """
    import time
    start_time = time.time()

    try:
        # 创建RAG Agent
        agent = agent_manager.create_agent("rag")

        # 构建消息历史
        messages = []
        if request.conversation_history:
            for msg in request.conversation_history:
                messages.append(msg.content)
        messages.append(request.question)

        # 构建状态和过滤条件
        filter_metadata = {"user_id": str(current_user.id)}
        if request.document_ids:
            filter_metadata["document_id"] = {"$in": request.document_ids}

        state = {
            "messages": messages,
            "metadata": {
                "user_id": str(current_user.id),
                "agent_type": "rag",
                "filter_metadata": filter_metadata
            },
            "status": "pending",
            "result": None,
            "error": None
        }

        # 执行RAG Agent
        result_state = await agent.execute(messages, state["metadata"])

        response_time = time.time() - start_time

        logger.info(f"文档问答完成: user_id={current_user.id}, 耗时={response_time:.2f}s")

        return ChatResponse(
            message=result_state["result"],
            agent_type="rag",
            response_time=response_time,
            metadata=result_state["metadata"]
        )

    except Exception as e:
        logger.error(f"文档问答失败: user_id={current_user.id}, error={str(e)}")
        response_time = time.time() - start_time

        return ChatResponse(
            message=f"抱歉，在回答您的问题时遇到问题：{str(e)}",
            agent_type="rag",
            response_time=response_time,
            metadata={"error": str(e)}
        )


@router.post("/search", response_model=ChatResponse)
async def smart_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user)
):
    """
    智能搜索

    Args:
        request: 搜索请求
        current_user: 当前用户

    Returns:
        ChatResponse: 搜索响应
    """
    import time
    start_time = time.time()

    try:
        # 创建Search Agent
        agent = agent_manager.create_agent("search")

        # 构建状态
        state = {
            "messages": [request.query],
            "metadata": {
                "user_id": str(current_user.id),
                "agent_type": "search",
                "filter_metadata": {"user_id": str(current_user.id)},
                "max_results": request.max_results
            },
            "status": "pending",
            "result": None,
            "error": None
        }

        # 执行Search Agent
        result_state = await agent.execute([request.query], state["metadata"])

        response_time = time.time() - start_time

        logger.info(f"智能搜索完成: user_id={current_user.id}, 耗时={response_time:.2f}s")

        return ChatResponse(
            message=result_state["result"],
            agent_type="search",
            response_time=response_time,
            metadata=result_state["metadata"]
        )

    except Exception as e:
        logger.error(f"智能搜索失败: user_id={current_user.id}, error={str(e)}")
        response_time = time.time() - start_time

        return ChatResponse(
            message=f"抱歉，搜索时遇到问题：{str(e)}",
            agent_type="search",
            response_time=response_time,
            metadata={"error": str(e)}
        )


@router.get("/agents", response_model=dict)
async def get_available_agents():
    """
    获取可用的Agent类型

    Returns:
        dict: 可用的Agent类型
    """
    return agent_manager.get_available_types()


@router.get("/health")
async def chat_health_check():
    """
    聊天服务健康检查

    Returns:
        dict: 健康状态
    """
    try:
        # 测试Agent创建
        agent = agent_manager.create_agent("chat")
        agent_manager.remove_agent(agent.id)

        return {
            "status": "healthy",
            "available_agents": list(agent_manager.get_available_types().keys()),
            "active_agents": len(agent_manager.list_agents())
        }

    except Exception as e:
        logger.error(f"聊天服务健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }