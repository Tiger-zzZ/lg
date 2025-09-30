"""
上下文处理器和动态上下文管理
"""

from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from app.core.logging import logger


@dataclass
class ContextItem:
    """上下文项"""
    key: str
    value: Any
    timestamp: datetime
    source: str  # user, system, agent, external
    priority: int = 1  # 1-10, 数字越大优先级越高
    expires_at: Optional[datetime] = None


class DynamicContext:
    """动态上下文管理"""

    def __init__(self, max_items: int = 100):
        self.max_items = max_items
        self._items: List[ContextItem] = []
        self._processors: List[Callable] = []

    def add_item(self, key: str, value: Any, source: str = "system",
                 priority: int = 1, ttl_seconds: Optional[int] = None):
        """添加上下文项"""
        expires_at = None
        if ttl_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)

        item = ContextItem(
            key=key,
            value=value,
            timestamp=datetime.utcnow(),
            source=source,
            priority=priority,
            expires_at=expires_at
        )

        # 移除重复键
        self._items = [i for i in self._items if i.key != key]

        # 添加新项
        self._items.append(item)

        # 清理过期项
        self._cleanup_expired()

        # 限制数量
        if len(self._items) > self.max_items:
            # 按优先级和时间排序，保留最重要的
            self._items.sort(key=lambda x: (x.priority, x.timestamp), reverse=True)
            self._items = self._items[:self.max_items]

        logger.debug(f"添加上下文项: {key} = {value}")

    def get_item(self, key: str) -> Optional[ContextItem]:
        """获取上下文项"""
        self._cleanup_expired()
        for item in self._items:
            if item.key == key:
                return item
        return None

    def get_value(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        item = self.get_item(key)
        return item.value if item else default

    def remove_item(self, key: str) -> bool:
        """移除上下文项"""
        initial_count = len(self._items)
        self._items = [i for i in self._items if i.key != key]
        return len(self._items) < initial_count

    def get_context_dict(self, sources: Optional[List[str]] = None,
                        min_priority: int = 1) -> Dict[str, Any]:
        """获取上下文字典"""
        self._cleanup_expired()

        filtered_items = self._items
        if sources:
            filtered_items = [i for i in filtered_items if i.source in sources]
        if min_priority > 1:
            filtered_items = [i for i in filtered_items if i.priority >= min_priority]

        return {item.key: item.value for item in filtered_items}

    def get_recent_context(self, minutes: int = 10) -> Dict[str, Any]:
        """获取最近的上下文"""
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        recent_items = [
            item for item in self._items
            if item.timestamp >= cutoff
        ]
        return {item.key: item.value for item in recent_items}

    def add_processor(self, processor: Callable):
        """添加上下文处理器"""
        self._processors.append(processor)

    def process_context(self, raw_context: Dict[str, Any]) -> Dict[str, Any]:
        """处理上下文"""
        processed = raw_context.copy()

        for processor in self._processors:
            try:
                processed = processor(processed)
            except Exception as e:
                logger.error(f"上下文处理器错误: {e}")

        return processed

    def _cleanup_expired(self):
        """清理过期项"""
        now = datetime.utcnow()
        self._items = [
            item for item in self._items
            if item.expires_at is None or item.expires_at > now
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        self._cleanup_expired()

        # 按来源统计
        source_counts = {}
        for item in self._items:
            source_counts[item.source] = source_counts.get(item.source, 0) + 1

        # 按优先级统计
        priority_counts = {}
        for item in self._items:
            priority_counts[item.priority] = priority_counts.get(item.priority, 0) + 1

        return {
            "total_items": len(self._items),
            "source_distribution": source_counts,
            "priority_distribution": priority_counts,
            "oldest_item": min(self._items, key=lambda x: x.timestamp).timestamp.isoformat() if self._items else None,
            "newest_item": max(self._items, key=lambda x: x.timestamp).timestamp.isoformat() if self._items else None
        }


class ContextProcessor:
    """上下文处理器"""

    @staticmethod
    def user_info_processor(context: Dict[str, Any]) -> Dict[str, Any]:
        """用户信息处理器"""
        if "user_id" in context:
            # 这里可以从数据库获取用户信息
            context["user_name"] = context.get("user_name", f"用户{context['user_id']}")
            context["user_preferences"] = context.get("user_preferences", {})

        return context

    @staticmethod
    def timestamp_processor(context: Dict[str, Any]) -> Dict[str, Any]:
        """时间戳处理器"""
        now = datetime.utcnow()
        context["current_time"] = now.isoformat()
        context["current_date"] = now.strftime("%Y-%m-%d")
        context["current_hour"] = now.hour

        # 时间相关的问候语
        if 5 <= now.hour < 12:
            context["time_greeting"] = "早上好"
        elif 12 <= now.hour < 18:
            context["time_greeting"] = "下午好"
        else:
            context["time_greeting"] = "晚上好"

        return context

    @staticmethod
    def conversation_processor(context: Dict[str, Any]) -> Dict[str, Any]:
        """对话上下文处理器"""
        # 处理对话历史
        if "conversation_history" in context:
            history = context["conversation_history"]
            if isinstance(history, list) and history:
                context["last_user_message"] = None
                context["last_assistant_message"] = None

                # 找到最后的用户消息和助手消息
                for msg in reversed(history):
                    if isinstance(msg, dict):
                        if msg.get("role") == "user" and not context["last_user_message"]:
                            context["last_user_message"] = msg.get("content", "")
                        elif msg.get("role") == "assistant" and not context["last_assistant_message"]:
                            context["last_assistant_message"] = msg.get("content", "")

                context["conversation_length"] = len(history)

        return context

    @staticmethod
    def task_context_processor(context: Dict[str, Any]) -> Dict[str, Any]:
        """任务上下文处理器"""
        if "task_type" in context:
            task_type = context["task_type"]

            # 根据任务类型设置相关提示
            task_hints = {
                "coding": "请提供清晰的代码示例和解释",
                "analysis": "请进行深入的分析并提供数据支持",
                "writing": "请注意文档结构和语言表达",
                "research": "请提供可靠的信息来源和多角度观点"
            }

            context["task_hint"] = task_hints.get(task_type, "请提供专业和有帮助的回答")

        return context

    @staticmethod
    def create_smart_context(base_context: Dict[str, Any],
                           user_context: Optional[DynamicContext] = None) -> Dict[str, Any]:
        """创建智能上下文"""
        # 基础上下文
        smart_context = base_context.copy()

        # 添加用户动态上下文
        if user_context:
            user_ctx = user_context.get_context_dict(min_priority=2)
            smart_context.update(user_ctx)

        # 应用处理器
        processors = [
            ContextProcessor.timestamp_processor,
            ContextProcessor.user_info_processor,
            ContextProcessor.conversation_processor,
            ContextProcessor.task_context_processor
        ]

        for processor in processors:
            try:
                smart_context = processor(smart_context)
            except Exception as e:
                logger.error(f"上下文处理器错误: {e}")

        return smart_context