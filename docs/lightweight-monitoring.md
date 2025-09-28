# 轻量级监控方案

## 监控策略：渐进式演进

### 第一阶段：内置监控 (MVP)
快速起步，无需额外基础设施

#### 健康检查
```python
# app/api/health.py
from fastapi import APIRouter
from app.core.monitoring import HealthChecker

router = APIRouter()

@router.get("/health")
async def health_check():
    """综合健康检查"""
    health_checker = HealthChecker()
    return await health_checker.check_all()

@router.get("/health/live")
async def liveness():
    """存活检查 - Kubernetes使用"""
    return {"status": "alive"}

@router.get("/health/ready")
async def readiness():
    """就绪检查 - Kubernetes使用"""
    health_checker = HealthChecker()
    return await health_checker.check_readiness()
```

#### 内置Metrics
```python
# app/core/monitoring.py
import time
import psutil
from typing import Dict, Any
from datetime import datetime

class SimpleMetrics:
    def __init__(self):
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0

    def get_system_metrics(self) -> Dict[str, Any]:
        """获取系统指标"""
        return {
            "uptime": time.time() - self.start_time,
            "cpu_percent": psutil.cpu_percent(),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_app_metrics(self) -> Dict[str, Any]:
        """获取应用指标"""
        return {
            "request_count": self.request_count,
            "error_count": self.error_count,
            "error_rate": self.error_count / max(self.request_count, 1),
            "timestamp": datetime.utcnow().isoformat()
        }

# 中间件记录请求
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    # 记录指标
    metrics.request_count += 1
    if response.status_code >= 400:
        metrics.error_count += 1

    # 添加响应时间头
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)

    return response
```

#### 结构化日志
```python
# app/core/logging.py
import structlog
import logging.config

def setup_logging():
    """配置结构化日志"""
    logging.config.dictConfig({
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "json": {
                "()": structlog.stdlib.ProcessorFormatter,
                "processor": structlog.dev.ConsoleRenderer(colors=False),
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
        },
        "root": {
            "level": "INFO",
            "handlers": ["console"],
        },
    })

    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

# 使用示例
logger = structlog.get_logger()

async def process_agent_task(agent_id: str, task_data: dict):
    logger.info(
        "agent_task_started",
        agent_id=agent_id,
        task_type=task_data.get("type"),
        user_id=task_data.get("user_id")
    )

    try:
        # 处理任务
        result = await execute_task(task_data)

        logger.info(
            "agent_task_completed",
            agent_id=agent_id,
            duration_ms=result.get("duration_ms"),
            token_usage=result.get("token_usage")
        )

    except Exception as e:
        logger.error(
            "agent_task_failed",
            agent_id=agent_id,
            error=str(e),
            task_type=task_data.get("type")
        )
        raise
```

### 第二阶段：外部监控 (扩展)

#### Prometheus + Grafana (可选)
```python
# app/core/metrics.py
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Response

# 定义指标
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('http_request_duration_seconds', 'HTTP request duration')
ACTIVE_AGENTS = Gauge('active_agents_total', 'Number of active agents')
RAG_QUERIES = Counter('rag_queries_total', 'Total RAG queries', ['status'])

@app.get("/metrics")
async def get_metrics():
    """Prometheus metrics endpoint"""
    return Response(generate_latest(), media_type="text/plain")

# 中间件
@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    # 记录指标
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path
    ).inc()

    REQUEST_DURATION.observe(time.time() - start_time)

    return response
```

#### 简单的监控面板
```python
# app/api/admin.py
@router.get("/admin/dashboard")
async def monitoring_dashboard():
    """简单的监控面板数据"""
    metrics = SimpleMetrics()

    # 数据库连接数
    db_pool_size = await get_db_pool_info()

    # Agent状态统计
    agent_stats = await get_agent_statistics()

    # 最近错误
    recent_errors = await get_recent_errors(limit=10)

    return {
        "system": metrics.get_system_metrics(),
        "application": metrics.get_app_metrics(),
        "database": db_pool_size,
        "agents": agent_stats,
        "recent_errors": recent_errors
    }
```

## 监控配置文件

### docker-compose.yml (包含监控)
```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    environment:
      - MONITORING_ENABLED=true
      - LOG_LEVEL=INFO
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # 可选：Prometheus (仅在需要时启用)
  prometheus:
    image: prom/prometheus:latest
    profiles: ["monitoring"]  # 只在指定profile时启动
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'

  # 可选：Grafana
  grafana:
    image: grafana/grafana:latest
    profiles: ["monitoring"]
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards
      - ./monitoring/grafana/datasources:/etc/grafana/provisioning/datasources

volumes:
  grafana_data:
```

### 启动命令
```bash
# 基础模式 (无外部监控)
docker-compose up -d

# 完整监控模式
docker-compose --profile monitoring up -d
```

### 简单的Prometheus配置
```yaml
# monitoring/prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'lg-platform-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 10s

  - job_name: 'lg-platform-health'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/health'
    scrape_interval: 30s
```

## 云原生监控

### Kubernetes监控
```yaml
# k8s/monitoring/servicemonitor.yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: lg-platform-backend
spec:
  selector:
    matchLabels:
      app: lg-platform-backend
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

### 云厂商集成
```python
# app/core/cloud_monitoring.py
import boto3  # AWS CloudWatch
from google.cloud import monitoring_v3  # Google Cloud Monitoring

class CloudMonitoring:
    def __init__(self, provider: str):
        self.provider = provider

    async def send_custom_metric(self, name: str, value: float, tags: dict = None):
        """发送自定义指标到云监控"""
        if self.provider == "aws":
            await self._send_to_cloudwatch(name, value, tags)
        elif self.provider == "gcp":
            await self._send_to_google_monitoring(name, value, tags)
        elif self.provider == "azure":
            await self._send_to_azure_monitor(name, value, tags)

    async def _send_to_cloudwatch(self, name: str, value: float, tags: dict):
        cloudwatch = boto3.client('cloudwatch')
        dimensions = [{'Name': k, 'Value': v} for k, v in tags.items()] if tags else []

        cloudwatch.put_metric_data(
            Namespace='LG-Platform',
            MetricData=[
                {
                    'MetricName': name,
                    'Value': value,
                    'Dimensions': dimensions
                }
            ]
        )
```

## 告警策略

### 基础告警
```python
# app/core/alerts.py
from typing import List, Dict
import asyncio
from datetime import datetime, timedelta

class SimpleAlerting:
    def __init__(self):
        self.thresholds = {
            'cpu_percent': 80,
            'memory_percent': 85,
            'error_rate': 0.05,  # 5%
            'response_time': 2.0  # 2秒
        }
        self.alert_history = []

    async def check_thresholds(self):
        """检查指标阈值"""
        metrics = SimpleMetrics()
        system_metrics = metrics.get_system_metrics()
        app_metrics = metrics.get_app_metrics()

        alerts = []

        # CPU检查
        if system_metrics['cpu_percent'] > self.thresholds['cpu_percent']:
            alerts.append({
                'type': 'cpu_high',
                'value': system_metrics['cpu_percent'],
                'threshold': self.thresholds['cpu_percent']
            })

        # 内存检查
        if system_metrics['memory_percent'] > self.thresholds['memory_percent']:
            alerts.append({
                'type': 'memory_high',
                'value': system_metrics['memory_percent'],
                'threshold': self.thresholds['memory_percent']
            })

        # 错误率检查
        if app_metrics['error_rate'] > self.thresholds['error_rate']:
            alerts.append({
                'type': 'error_rate_high',
                'value': app_metrics['error_rate'],
                'threshold': self.thresholds['error_rate']
            })

        # 发送告警
        for alert in alerts:
            await self.send_alert(alert)

    async def send_alert(self, alert: Dict):
        """发送告警通知"""
        # 可以发送到多个渠道
        await asyncio.gather(
            self._log_alert(alert),
            self._send_webhook(alert),  # 可选
            # self._send_email(alert),  # 可选
            # self._send_slack(alert),  # 可选
        )

    async def _log_alert(self, alert: Dict):
        logger.warning(
            "alert_triggered",
            alert_type=alert['type'],
            current_value=alert['value'],
            threshold=alert['threshold'],
            timestamp=datetime.utcnow().isoformat()
        )
```

## 性能监控

### 数据库查询监控
```python
# app/core/db_monitoring.py
import time
from sqlalchemy.event import listens_for
from sqlalchemy.engine import Engine

@listens_for(Engine, "before_cursor_execute")
def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    context._query_start_time = time.time()

@listens_for(Engine, "after_cursor_execute")
def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
    total = time.time() - context._query_start_time

    # 记录慢查询
    if total > 1.0:  # 超过1秒的查询
        logger.warning(
            "slow_query_detected",
            duration=total,
            query=statement[:200],  # 截断长查询
            parameters=str(parameters)[:100] if parameters else None
        )
```

### Agent执行监控
```python
# app/agents/monitoring.py
import functools
import time

def monitor_agent_execution(func):
    """Agent执行监控装饰器"""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        agent_id = kwargs.get('agent_id', 'unknown')

        try:
            result = await func(*args, **kwargs)

            # 记录成功执行
            duration = time.time() - start_time
            logger.info(
                "agent_execution_success",
                agent_id=agent_id,
                duration=duration,
                result_size=len(str(result)) if result else 0
            )

            # 更新指标
            if 'ACTIVE_AGENTS' in globals():
                ACTIVE_AGENTS.inc()

            return result

        except Exception as e:
            # 记录执行失败
            duration = time.time() - start_time
            logger.error(
                "agent_execution_failed",
                agent_id=agent_id,
                duration=duration,
                error=str(e),
                error_type=type(e).__name__
            )

            # 更新错误指标
            if 'RAG_QUERIES' in globals():
                RAG_QUERIES.labels(status='failed').inc()

            raise

    return wrapper
```

这个轻量级监控方案的优势：

1. **快速起步**: 内置监控无需额外基础设施
2. **渐进演进**: 可以根据需要逐步增加监控组件
3. **云原生友好**: 支持Kubernetes健康检查和指标采集
4. **开发友好**: 结构化日志便于开发调试
5. **成本可控**: 基础监控几乎零成本，扩展监控按需启用