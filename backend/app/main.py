from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import time
import psutil
from datetime import datetime
from contextlib import asynccontextmanager

from .core.config import settings
from .core.logging import setup_logging
from .api.routes import api_router

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
    print(f"🚀 LG Platform Backend starting...")
    print(f"📖 API文档: http://localhost:8000/docs")
    print(f"🔍 Health Check: http://localhost:8000/health")

    yield

    # 关闭时执行
    print("👋 LG Platform Backend shutting down...")


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
async def metrics_middleware(request, call_next):
    """请求计数中间件"""
    global request_count, error_count

    start_time_req = time.time()
    request_count += 1

    response = await call_next(request)

    # 记录错误
    if response.status_code >= 400:
        error_count += 1

    # 添加响应时间
    process_time = time.time() - start_time_req
    response.headers["X-Process-Time"] = str(process_time)

    return response


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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )