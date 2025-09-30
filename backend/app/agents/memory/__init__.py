"""
Agent记忆机制
实现短期记忆、长期记忆和上下文管理
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json
import uuid
import asyncio

from app.core.logging import logger
from .storage import memory_storage


class MemoryType(Enum):
    """记忆类型"""
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    EPISODIC = "episodic"
    PROCEDURAL = "procedural"


class MemoryImportance(Enum):
    """记忆重要性"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class Memory:
    """记忆项"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    content: str = ""
    memory_type: MemoryType = MemoryType.SHORT_TERM
    importance: MemoryImportance = MemoryImportance.MEDIUM
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    expires_at: Optional[datetime] = None


class AgentMemory:
    """Agent记忆管理器 - Docker环境优化版"""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.short_term_cache: Dict[str, Memory] = {}
        self.max_short_term = 50

    async def remember(self, content: str, memory_type: MemoryType = MemoryType.SHORT_TERM,
                      importance: MemoryImportance = MemoryImportance.MEDIUM,
                      tags: List[str] = None, metadata: Dict[str, Any] = None,
                      ttl_hours: Optional[int] = None) -> str:
        """存储新记忆"""
        memory = Memory(
            agent_id=self.agent_id,
            content=content,
            memory_type=memory_type,
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )

        if ttl_hours:
            memory.expires_at = datetime.utcnow() + timedelta(hours=ttl_hours)

        # 存储到数据库
        success = await memory_storage.store_memory(memory)

        # 如果是短期记忆，也存储到缓存
        if memory_type == MemoryType.SHORT_TERM and success:
            self._add_to_short_term_cache(memory)

        if success:
            logger.info(f"存储记忆成功: {memory.id}")
            return memory.id
        else:
            logger.error(f"存储记忆失败: {content[:50]}...")
            raise Exception("记忆存储失败")

    async def recall(self, query: str, memory_type: Optional[MemoryType] = None,
                    limit: int = 10) -> List[Memory]:
        """检索相关记忆"""
        try:
            # 首先检查短期记忆缓存
            cache_results = []
            if memory_type in [None, MemoryType.SHORT_TERM]:
                cache_results = self._search_short_term_cache(query, limit)

            # 如果缓存结果足够，直接返回
            if len(cache_results) >= limit:
                return cache_results[:limit]

            # 从数据库搜索
            remaining_limit = limit - len(cache_results)
            storage_results = await memory_storage.search_memories(
                self.agent_id, query, memory_type, remaining_limit
            )

            # 合并结果并去重
            all_results = cache_results + storage_results
            unique_results = []
            seen_ids = set()

            for memory in all_results:
                if memory.id not in seen_ids:
                    unique_results.append(memory)
                    seen_ids.add(memory.id)

            return unique_results[:limit]

        except Exception as e:
            logger.error(f"检索记忆失败: {e}")
            return []

    async def forget(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            # 从缓存删除
            if memory_id in self.short_term_cache:
                del self.short_term_cache[memory_id]

            # 从数据库删除
            return await memory_storage.delete_memory(memory_id)

        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            return False

    async def get_memory_summary(self) -> Dict[str, Any]:
        """获取记忆摘要"""
        try:
            short_term_count = len(self.short_term_cache)

            return {
                "agent_id": self.agent_id,
                "short_term_count": short_term_count,
                "last_activity": datetime.utcnow().isoformat()
            }

        except Exception as e:
            logger.error(f"获取记忆摘要失败: {e}")
            return {}

    def _add_to_short_term_cache(self, memory: Memory):
        """添加到短期记忆缓存"""
        self.short_term_cache[memory.id] = memory

        # 限制缓存大小
        if len(self.short_term_cache) > self.max_short_term:
            # 删除最老的记忆
            oldest_id = min(
                self.short_term_cache.keys(),
                key=lambda x: self.short_term_cache[x].created_at
            )
            del self.short_term_cache[oldest_id]

    def _search_short_term_cache(self, query: str, limit: int) -> List[Memory]:
        """搜索短期记忆缓存"""
        query_lower = query.lower()
        matches = []

        for memory in self.short_term_cache.values():
            if (query_lower in memory.content.lower() or
                any(query_lower in tag.lower() for tag in memory.tags)):
                matches.append(memory)

        # 按重要性和时间排序
        matches.sort(
            key=lambda x: (x.importance.value, x.last_accessed),
            reverse=True
        )

        return matches[:limit]
