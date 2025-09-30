"""
性能监控系统
收集和分析系统性能指标
"""
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import time
import asyncio
from collections import defaultdict, deque

from app.core.logging import logger


class MetricType(Enum):
    """指标类型"""
    COUNTER = "counter"  # 计数器
    GAUGE = "gauge"  # 仪表
    HISTOGRAM = "histogram"  # 直方图
    TIMER = "timer"  # 计时器


@dataclass
class Metric:
    """性能指标"""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class PerformanceStats:
    """性能统计"""
    total_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_duration_ms: float = 0.0
    min_duration_ms: float = float('inf')
    max_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0

    def update(self, duration_ms: float, success: bool = True):
        """更新统计"""
        self.total_count += 1
        if success:
            self.success_count += 1
        else:
            self.failure_count += 1

        self.total_duration_ms += duration_ms
        self.min_duration_ms = min(self.min_duration_ms, duration_ms)
        self.max_duration_ms = max(self.max_duration_ms, duration_ms)
        self.avg_duration_ms = self.total_duration_ms / self.total_count

    @property
    def success_rate(self) -> float:
        """成功率"""
        if self.total_count == 0:
            return 0.0
        return (self.success_count / self.total_count) * 100

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "total_count": self.total_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "success_rate": round(self.success_rate, 2),
            "total_duration_ms": round(self.total_duration_ms, 2),
            "min_duration_ms": round(self.min_duration_ms, 2) if self.min_duration_ms != float('inf') else 0,
            "max_duration_ms": round(self.max_duration_ms, 2),
            "avg_duration_ms": round(self.avg_duration_ms, 2)
        }


class MetricsCollector:
    """性能指标收集器"""

    def __init__(self, max_history_size: int = 1000):
        self.max_history_size = max_history_size

        # 指标存储
        self._counters: Dict[str, float] = defaultdict(float)
        self._gauges: Dict[str, float] = {}
        self._histograms: Dict[str, deque] = defaultdict(lambda: deque(maxlen=max_history_size))
        self._timers: Dict[str, List[float]] = defaultdict(list)

        # 性能统计
        self._stats: Dict[str, PerformanceStats] = defaultdict(PerformanceStats)

        # 指标历史
        self._metric_history: deque = deque(maxlen=max_history_size)

    def increment_counter(self, name: str, value: float = 1.0, tags: Optional[Dict[str, str]] = None):
        """增加计数器"""
        self._counters[name] += value
        self._record_metric(name, value, MetricType.COUNTER, tags)
        logger.debug(f"计数器增加: {name} +{value}")

    def set_gauge(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """设置仪表值"""
        self._gauges[name] = value
        self._record_metric(name, value, MetricType.GAUGE, tags)
        logger.debug(f"仪表设置: {name} = {value}")

    def record_histogram(self, name: str, value: float, tags: Optional[Dict[str, str]] = None):
        """记录直方图值"""
        self._histograms[name].append(value)
        self._record_metric(name, value, MetricType.HISTOGRAM, tags)
        logger.debug(f"直方图记录: {name} = {value}")

    def record_timer(self, name: str, duration_ms: float, success: bool = True,
                    tags: Optional[Dict[str, str]] = None):
        """记录计时器"""
        self._timers[name].append(duration_ms)
        self._stats[name].update(duration_ms, success)
        self._record_metric(name, duration_ms, MetricType.TIMER, tags)
        logger.debug(f"计时器记录: {name} = {duration_ms}ms (success={success})")

    def _record_metric(self, name: str, value: float, metric_type: MetricType,
                      tags: Optional[Dict[str, str]]):
        """记录指标到历史"""
        metric = Metric(
            name=name,
            value=value,
            metric_type=metric_type,
            tags=tags or {}
        )
        self._metric_history.append(metric)

    def get_counter(self, name: str) -> float:
        """获取计数器值"""
        return self._counters.get(name, 0.0)

    def get_gauge(self, name: str) -> Optional[float]:
        """获取仪表值"""
        return self._gauges.get(name)

    def get_histogram_stats(self, name: str) -> Dict[str, float]:
        """获取直方图统计"""
        values = list(self._histograms.get(name, []))
        if not values:
            return {}

        values_sorted = sorted(values)
        length = len(values_sorted)

        return {
            "count": length,
            "min": min(values),
            "max": max(values),
            "avg": sum(values) / length,
            "p50": values_sorted[int(length * 0.5)] if length > 0 else 0,
            "p90": values_sorted[int(length * 0.9)] if length > 0 else 0,
            "p95": values_sorted[int(length * 0.95)] if length > 0 else 0,
            "p99": values_sorted[int(length * 0.99)] if length > 0 else 0,
        }

    def get_stats(self, name: str) -> Dict[str, Any]:
        """获取性能统计"""
        return self._stats.get(name, PerformanceStats()).to_dict()

    def get_all_counters(self) -> Dict[str, float]:
        """获取所有计数器"""
        return dict(self._counters)

    def get_all_gauges(self) -> Dict[str, float]:
        """获取所有仪表"""
        return dict(self._gauges)

    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有统计"""
        return {name: stats.to_dict() for name, stats in self._stats.items()}

    def get_recent_metrics(self, limit: int = 100) -> List[Dict[str, Any]]:
        """获取最近的指标"""
        metrics = list(self._metric_history)[-limit:]
        return [
            {
                "name": m.name,
                "value": m.value,
                "type": m.metric_type.value,
                "tags": m.tags,
                "timestamp": m.timestamp.isoformat()
            }
            for m in metrics
        ]

    def reset(self):
        """重置所有指标"""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._timers.clear()
        self._stats.clear()
        self._metric_history.clear()
        logger.info("指标收集器已重置")


class PerformanceMonitor:
    """性能监控器"""

    def __init__(self, collector: MetricsCollector):
        self.collector = collector
        self._monitoring = False
        self._monitor_task: Optional[asyncio.Task] = None

    async def start_monitoring(self, interval: float = 60.0):
        """开始监控"""
        if self._monitoring:
            logger.warning("性能监控已在运行")
            return

        self._monitoring = True
        self._monitor_task = asyncio.create_task(self._monitor_loop(interval))
        logger.info(f"性能监控已启动 (间隔: {interval}秒)")

    async def stop_monitoring(self):
        """停止监控"""
        self._monitoring = False
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        logger.info("性能监控已停止")

    async def _monitor_loop(self, interval: float):
        """监控循环"""
        while self._monitoring:
            try:
                await self._collect_system_metrics()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"监控循环错误: {str(e)}")
                await asyncio.sleep(interval)

    async def _collect_system_metrics(self):
        """收集系统指标"""
        try:
            import psutil

            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            self.collector.set_gauge("system.cpu.percent", cpu_percent)

            # 内存使用
            memory = psutil.virtual_memory()
            self.collector.set_gauge("system.memory.percent", memory.percent)
            self.collector.set_gauge("system.memory.available_mb", memory.available / 1024 / 1024)

            # 磁盘使用
            disk = psutil.disk_usage('/')
            self.collector.set_gauge("system.disk.percent", disk.percent)

            logger.debug(f"系统指标已收集: CPU={cpu_percent}%, Memory={memory.percent}%")

        except ImportError:
            logger.warning("psutil未安装,无法收集系统指标")
        except Exception as e:
            logger.error(f"收集系统指标失败: {str(e)}")

    def get_summary(self) -> Dict[str, Any]:
        """获取监控摘要"""
        return {
            "counters": self.collector.get_all_counters(),
            "gauges": self.collector.get_all_gauges(),
            "stats": self.collector.get_all_stats(),
            "monitoring": self._monitoring
        }


class PerformanceTimer:
    """性能计时器上下文管理器"""

    def __init__(self, collector: MetricsCollector, name: str, tags: Optional[Dict[str, str]] = None):
        self.collector = collector
        self.name = name
        self.tags = tags
        self.start_time: Optional[float] = None
        self.success = True

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.success = exc_type is None
            self.collector.record_timer(self.name, duration_ms, self.success, self.tags)

    async def __aenter__(self):
        self.start_time = time.time()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            duration_ms = (time.time() - self.start_time) * 1000
            self.success = exc_type is None
            self.collector.record_timer(self.name, duration_ms, self.success, self.tags)


# 全局指标收集器
global_metrics_collector = MetricsCollector()
global_performance_monitor = PerformanceMonitor(global_metrics_collector)


def get_metrics_collector() -> MetricsCollector:
    """获取全局指标收集器"""
    return global_metrics_collector


def get_performance_monitor() -> PerformanceMonitor:
    """获取全局性能监控器"""
    return global_performance_monitor