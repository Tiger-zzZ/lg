"""
统一错误处理和重试机制
提供装饰器和策略模式的错误处理框架
"""
from typing import Optional, Callable, Any, Type, Tuple, Dict
from enum import Enum
from dataclasses import dataclass, field
import asyncio
import time
import traceback
from functools import wraps

from app.core.logging import logger


class ErrorCategory(Enum):
    """错误类别"""
    NETWORK = "network"  # 网络相关错误
    DATABASE = "database"  # 数据库错误
    VALIDATION = "validation"  # 验证错误
    BUSINESS = "business"  # 业务逻辑错误
    EXTERNAL_API = "external_api"  # 外部API错误
    TIMEOUT = "timeout"  # 超时错误
    RESOURCE = "resource"  # 资源相关错误
    UNKNOWN = "unknown"  # 未知错误


class RecoveryAction(Enum):
    """恢复动作"""
    RETRY = "retry"  # 重试
    FALLBACK = "fallback"  # 使用备用方案
    SKIP = "skip"  # 跳过
    ABORT = "abort"  # 中止
    ESCALATE = "escalate"  # 升级处理


@dataclass
class RetryPolicy:
    """重试策略"""
    max_attempts: int = 3  # 最大重试次数
    initial_delay: float = 1.0  # 初始延迟(秒)
    max_delay: float = 60.0  # 最大延迟(秒)
    backoff_factor: float = 2.0  # 退避因子(指数退避)
    jitter: bool = True  # 是否添加随机抖动

    # 可重试的异常类型
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ConnectionError,
        TimeoutError,
        asyncio.TimeoutError,
    )


@dataclass
class ErrorContext:
    """错误上下文"""
    exception: Exception
    category: ErrorCategory
    recovery_action: RecoveryAction
    attempt: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    traceback: Optional[str] = None

    def __post_init__(self):
        if self.traceback is None:
            self.traceback = traceback.format_exc()


class ErrorClassifier:
    """错误分类器"""

    @staticmethod
    def classify(exception: Exception) -> ErrorCategory:
        """分类错误"""
        exception_type = type(exception).__name__
        exception_msg = str(exception).lower()

        # 网络错误
        if isinstance(exception, (ConnectionError, ConnectionRefusedError, ConnectionResetError)):
            return ErrorCategory.NETWORK

        # 超时错误
        if isinstance(exception, (TimeoutError, asyncio.TimeoutError)):
            return ErrorCategory.TIMEOUT

        # 数据库错误
        if "database" in exception_msg or "sql" in exception_msg:
            return ErrorCategory.DATABASE

        # 验证错误
        if "validation" in exception_msg or isinstance(exception, ValueError):
            return ErrorCategory.VALIDATION

        # 资源错误
        if isinstance(exception, (MemoryError, OSError)):
            return ErrorCategory.RESOURCE

        return ErrorCategory.UNKNOWN

    @staticmethod
    def is_retryable(exception: Exception, policy: RetryPolicy) -> bool:
        """判断错误是否可重试"""
        return isinstance(exception, policy.retryable_exceptions)


class RetryStrategy:
    """重试策略实现"""

    @staticmethod
    def calculate_delay(attempt: int, policy: RetryPolicy) -> float:
        """计算重试延迟"""
        # 指数退避
        delay = min(
            policy.initial_delay * (policy.backoff_factor ** (attempt - 1)),
            policy.max_delay
        )

        # 添加抖动
        if policy.jitter:
            import random
            delay = delay * (0.5 + random.random())

        return delay

    @staticmethod
    async def execute_with_retry(
        func: Callable,
        policy: RetryPolicy,
        *args,
        **kwargs
    ) -> Any:
        """执行函数并在失败时重试"""
        last_exception = None

        for attempt in range(1, policy.max_attempts + 1):
            try:
                logger.debug(f"尝试执行 {func.__name__}, 第 {attempt}/{policy.max_attempts} 次")

                # 执行函数
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                logger.info(f"执行成功: {func.__name__} (尝试 {attempt} 次)")
                return result

            except Exception as e:
                last_exception = e
                category = ErrorClassifier.classify(e)

                logger.warning(
                    f"执行失败: {func.__name__} (尝试 {attempt}/{policy.max_attempts})",
                    error=str(e),
                    category=category.value
                )

                # 判断是否应该重试
                if not ErrorClassifier.is_retryable(e, policy):
                    logger.error(f"错误不可重试: {type(e).__name__}")
                    raise

                # 如果还有重试机会
                if attempt < policy.max_attempts:
                    delay = RetryStrategy.calculate_delay(attempt, policy)
                    logger.info(f"等待 {delay:.2f}秒 后重试...")
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"达到最大重试次数: {policy.max_attempts}")

        # 所有重试都失败
        raise last_exception


class CircuitBreaker:
    """熔断器模式实现"""

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: Type[Exception] = Exception
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "closed"  # closed, open, half_open

    def call(self, func: Callable) -> Callable:
        """装饰器方法"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if self.state == "open":
                if time.time() - self.last_failure_time >= self.recovery_timeout:
                    self.state = "half_open"
                    logger.info(f"熔断器进入半开状态: {func.__name__}")
                else:
                    raise Exception(f"熔断器开启,拒绝调用: {func.__name__}")

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                # 成功调用
                if self.state == "half_open":
                    self.state = "closed"
                    self.failure_count = 0
                    logger.info(f"熔断器恢复关闭状态: {func.__name__}")

                return result

            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                logger.warning(
                    f"熔断器记录失败: {func.__name__} ({self.failure_count}/{self.failure_threshold})"
                )

                if self.failure_count >= self.failure_threshold:
                    self.state = "open"
                    logger.error(f"熔断器开启: {func.__name__}")

                raise

        return wrapper


class ErrorHandler:
    """统一错误处理器"""

    def __init__(self):
        self.error_handlers: Dict[ErrorCategory, Callable] = {}
        self.default_policy = RetryPolicy()

    def register_handler(self, category: ErrorCategory, handler: Callable):
        """注册错误处理器"""
        self.error_handlers[category] = handler
        logger.info(f"注册错误处理器: {category.value}")

    async def handle_error(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ) -> ErrorContext:
        """处理错误"""
        # 分类错误
        category = ErrorClassifier.classify(exception)

        # 确定恢复动作
        recovery_action = self._determine_recovery_action(exception, category)

        # 创建错误上下文
        error_ctx = ErrorContext(
            exception=exception,
            category=category,
            recovery_action=recovery_action,
            metadata=context or {}
        )

        logger.error(
            f"处理错误: {type(exception).__name__}",
            category=category.value,
            recovery_action=recovery_action.value,
            error=str(exception)
        )

        # 调用注册的处理器
        if category in self.error_handlers:
            try:
                await self.error_handlers[category](error_ctx)
            except Exception as e:
                logger.error(f"错误处理器执行失败: {str(e)}")

        return error_ctx

    def _determine_recovery_action(
        self,
        exception: Exception,
        category: ErrorCategory
    ) -> RecoveryAction:
        """确定恢复动作"""
        # 可重试的错误
        if category in [ErrorCategory.NETWORK, ErrorCategory.TIMEOUT, ErrorCategory.EXTERNAL_API]:
            return RecoveryAction.RETRY

        # 验证错误 - 跳过
        if category == ErrorCategory.VALIDATION:
            return RecoveryAction.SKIP

        # 业务错误 - 升级
        if category == ErrorCategory.BUSINESS:
            return RecoveryAction.ESCALATE

        # 默认 - 中止
        return RecoveryAction.ABORT


# 装饰器: 自动重试
def auto_retry(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """自动重试装饰器"""
    policy = RetryPolicy(
        max_attempts=max_attempts,
        initial_delay=initial_delay,
        backoff_factor=backoff_factor,
        retryable_exceptions=retryable_exceptions
    )

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await RetryStrategy.execute_with_retry(
                func, policy, *args, **kwargs
            )
        return wrapper
    return decorator


# 装饰器: 错误捕获和处理
def handle_errors(error_handler: ErrorHandler, context: Optional[Dict[str, Any]] = None):
    """错误处理装饰器"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)
            except Exception as e:
                error_ctx = await error_handler.handle_error(e, context)

                # 根据恢复动作决定是否重新抛出
                if error_ctx.recovery_action == RecoveryAction.ABORT:
                    raise

                return None

        return wrapper
    return decorator