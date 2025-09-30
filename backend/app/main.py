from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import psutil
import uuid
import traceback
from datetime import datetime
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logging import setup_logging, logger
from app.api.routes import api_router

# 设置日志
setup_logging()

# 启动时间记录
start_time = time.time()
request_count = 0
error_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 LG Platform Backend starting...",
                environment=settings.ENVIRONMENT,
                debug_mode=settings.DEBUG)
    logger.info("📖 API文档", docs_url="http://localhost:8000/docs")
    logger.info("🔍 Health Check", health_url="http://localhost:8000/health")
    logger.info("💾 数据库配置", database_url=settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'masked')
    logger.info("🔗 ChromaDB配置", chroma_host=settings.CHROMA_HOST, chroma_port=settings.CHROMA_PORT)

    yield

    # 关闭时执行
    logger.info("👋 LG Platform Backend shutting down...")


# 创建FastAPI应用
app = FastAPI(
    title="LG Platform API",
    description="LangGraph Multi-Agent Platform Backend",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS,
)


@app.middleware("http")
async def enhanced_logging_middleware(request: Request, call_next):
    """增强的请求日志中间件"""
    global request_count, error_count

    # 生成请求ID
    request_id = str(uuid.uuid4())[:8]
    start_time = time.time()
    request_count += 1

    # 记录请求开始
    logger.info("📥 HTTP请求开始",
                request_id=request_id,
                method=request.method,
                url=str(request.url),
                client_ip=request.client.host if request.client else "unknown",
                user_agent=request.headers.get("user-agent", "unknown"),
                content_type=request.headers.get("content-type"),
                content_length=request.headers.get("content-length"))

    try:
        # 执行请求
        response = await call_next(request)

        # 计算处理时间
        process_time = time.time() - start_time

        # 记录响应
        if response.status_code >= 400:
            error_count += 1
            logger.warning("📤 HTTP请求完成(错误)",
                          request_id=request_id,
                          status_code=response.status_code,
                          process_time=f"{process_time:.3f}s",
                          error=True)
        else:
            logger.info("📤 HTTP请求完成",
                       request_id=request_id,
                       status_code=response.status_code,
                       process_time=f"{process_time:.3f}s")

        # 添加响应头
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)

        return response

    except Exception as e:
        error_count += 1
        process_time = time.time() - start_time

        logger.error("💥 HTTP请求异常",
                    request_id=request_id,
                    error=str(e),
                    traceback=traceback.format_exc(),
                    process_time=f"{process_time:.3f}s")

        # 返回500错误
        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal Server Error",
                "request_id": request_id,
                "error": str(e) if settings.DEBUG else "Internal Server Error"
            },
            headers={"X-Request-ID": request_id}
        )


# 根路由
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": "🚀 LG Platform API is running!",
        "version": "0.1.0",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


# 健康检查端点
@app.get("/health")
async def health_check():
    """综合健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": time.time() - start_time,
        "version": "0.1.0"
    }


@app.get("/health/live")
async def liveness():
    """存活检查 - Kubernetes使用"""
    return {"status": "alive"}


@app.get("/health/ready")
async def readiness():
    """就绪检查 - Kubernetes使用"""
    # TODO: 检查数据库和其他依赖服务
    return {"status": "ready"}


# 内置监控端点
@app.get("/metrics")
async def get_metrics():
    """简单的监控指标"""
    return {
        "system": {
            "uptime": time.time() - start_time,
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
        },
        "application": {
            "request_count": request_count,
            "error_count": error_count,
            "error_rate": error_count / max(request_count, 1),
        },
        "timestamp": datetime.utcnow().isoformat()
    }


# 包含API路由
app.include_router(api_router, prefix="/api/v1")


# 调试端点
@app.get("/debug/config")
async def debug_config():
    """调试配置信息 (仅在DEBUG模式下可用)"""
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not Found")

    return {
        "environment": settings.ENVIRONMENT,
        "debug": settings.DEBUG,
        "log_level": settings.LOG_LEVEL,
        "database_url": "***masked***",
        "redis_url": settings.REDIS_URL.split('@')[1] if '@' in settings.REDIS_URL else settings.REDIS_URL,
        "chroma_host": settings.CHROMA_HOST,
        "chroma_port": settings.CHROMA_PORT,
        "openai_base_url": settings.OPENAI_BASE_URL,
        "openai_model": settings.OPENAI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "openai_api_key": settings.OPENAI_API_KEY[:10] + "***" if settings.OPENAI_API_KEY else "未配置"
    }


@app.get("/debug/logs")
async def debug_recent_logs():
    """获取最近的日志信息 (仅在DEBUG模式下可用)"""
    if not settings.DEBUG:
        raise HTTPException(status_code=404, detail="Not Found")

    try:
        from pathlib import Path
        import os

        log_dir = Path("/app/app/log")
        if not log_dir.exists():
            return {"message": "日志目录不存在", "logs": []}

        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"lg-backend-{today}.log"

        if not log_file.exists():
            return {"message": "今日日志文件不存在", "logs": []}

        # 读取最后50行
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-50:] if len(lines) > 50 else lines

        return {
            "log_file": str(log_file),
            "total_lines": len(lines),
            "recent_logs": [line.strip() for line in recent_lines]
        }

    except Exception as e:
        logger.error("获取调试日志失败", error=str(e))
        return {"error": str(e)}


# 快速模型测试端点 - 使用正确的模型名称
@app.get("/test/models-fixed")
async def test_models_fixed():
    """测试第三方模型连接 - 使用正确的模型名称"""
    from app.core.config import settings
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    import asyncio
    # from langchain_community.embeddings import ModelScopeEmbeddings
    # 使用正确的模型名称
    correct_llm_model = "deepseek-ai/DeepSeek-R1-0528-Qwen3-8B"
    correct_embedding_model = "BAAI/bge-large-zh-v1.5"

    results = {
        "config": {
            "api_key": settings.OPENAI_API_KEY[:10] + "..." if settings.OPENAI_API_KEY else "未配置",
            "base_url": settings.OPENAI_BASE_URL,
            "llm_model_used": correct_llm_model,
            "embedding_model_used": correct_embedding_model
        },
        "llm_test": {"status": "未测试", "error": None},
        "embedding_test": {"status": "未测试", "error": None}
    }

    # 测试LLM
    try:
        llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            model=correct_llm_model,
            temperature=0.1,
            max_tokens=50
        )

        # 这里不会阻塞主线程，因为asyncio.to_thread会在后台线程中执行llm.invoke，主线程会等待结果返回（即await），但不会阻塞事件循环的其他任务。
        response = await asyncio.to_thread(
            llm.invoke, "说'你好'"
        )
        results["llm_test"] = {
            "status": "成功",
            "response": response.content[:100],
            "error": None
        }
    except Exception as e:
        results["llm_test"] = {
            "status": "失败",
            "response": None,
            "error": str(e)
        }

    # 测试Embedding
    try:
        embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            model=correct_embedding_model
        )

        embedding = await asyncio.to_thread(
            embeddings.embed_query, "测试文本"
        )
        results["embedding_test"] = {
            "status": "成功",
            "dimension": len(embedding),
            "sample": embedding[:5],
            "error": None
        }
    except Exception as e:
        results["embedding_test"] = {
            "status": "失败",
            "dimension": 0,
            "sample": None,
            "error": str(e)
        }

    return results


# 模型测试端点
@app.get("/test/models")
async def test_models():
    """测试第三方模型连接"""
    from app.core.config import settings
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    import asyncio

    results = {
        "config": {
            "api_key": settings.OPENAI_API_KEY[:10] + "..." if settings.OPENAI_API_KEY else "未配置",
            "base_url": settings.OPENAI_BASE_URL,
            "llm_model": settings.OPENAI_MODEL,
            "embedding_model": settings.EMBEDDING_MODEL
        },
        "llm_test": {"status": "未测试", "error": None},
        "embedding_test": {"status": "未测试", "error": None}
    }

    # 测试LLM
    try:
        llm = ChatOpenAI(
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            model=settings.OPENAI_MODEL,
            temperature=0.1,
            max_tokens=50
        )

        response = await asyncio.to_thread(
            llm.invoke, "说'你好'"
        )
        results["llm_test"] = {
            "status": "成功",
            "response": response.content[:100],
            "error": None
        }
    except Exception as e:
        results["llm_test"] = {
            "status": "失败",
            "response": None,
            "error": str(e)
        }

    # 测试Embedding
    try:
        embeddings = OpenAIEmbeddings(
            openai_api_key=settings.OPENAI_API_KEY,
            openai_api_base=settings.OPENAI_BASE_URL,
            model=settings.EMBEDDING_MODEL
        )

        embedding = await asyncio.to_thread(
            embeddings.embed_query, "测试文本"
        )
        results["embedding_test"] = {
            "status": "成功",
            "dimension": len(embedding),
            "sample": embedding[:5],
            "error": None
        }
    except Exception as e:
        results["embedding_test"] = {
            "status": "失败",
            "dimension": 0,
            "sample": None,
            "error": str(e)
        }

    return results


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="debug"
    )