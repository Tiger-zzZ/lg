"""
SQLAlchemy记忆存储实现
适配Docker环境和现有数据库连接
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy import text
from app.core.database import SessionLocal
from app.core.logging import logger


class SQLAlchemyMemoryStorage:
    """SQLAlchemy记忆存储"""

    def __init__(self):
        pass

    def get_db_session(self):
        """获取数据库会话"""
        return SessionLocal()

    async def store_memory(self, memory) -> bool:
        """存储记忆到PostgreSQL"""
        try:
            db = self.get_db_session()

            query = text("""
            INSERT INTO agent_memories (
                id, agent_id, content, memory_type, importance,
                tags, metadata, created_at, last_accessed, access_count, expires_at
            ) VALUES (:id, :agent_id, :content, :memory_type, :importance,
                      :tags, :metadata, :created_at, :last_accessed, :access_count, :expires_at)
            """)

            db.execute(query, {
                "id": memory.id,
                "agent_id": memory.agent_id,
                "content": memory.content,
                "memory_type": memory.memory_type.value,
                "importance": memory.importance.value,
                "tags": json.dumps(memory.tags),
                "metadata": json.dumps(memory.metadata),
                "created_at": memory.created_at,
                "last_accessed": memory.last_accessed,
                "access_count": memory.access_count,
                "expires_at": memory.expires_at
            })

            db.commit()
            logger.debug(f"存储记忆: {memory.id} for agent {memory.agent_id}")
            return True

        except Exception as e:
            logger.error(f"存储记忆失败: {e}")
            if db:
                db.rollback()
            return False
        finally:
            if db:
                db.close()

    async def search_memories(self, agent_id: str, query: str,
                            memory_type=None, limit: int = 10) -> List:
        """搜索记忆"""
        try:
            db = self.get_db_session()

            # 构建查询条件
            conditions = ["agent_id = :agent_id"]
            params = {"agent_id": agent_id}

            if memory_type:
                conditions.append("memory_type = :memory_type")
                params["memory_type"] = memory_type.value

            # 使用全文搜索
            conditions.append("content ILIKE :query")
            params["query"] = f"%{query}%"

            # 构建完整查询
            where_clause = " AND ".join(conditions)
            sql_query = f"""
            SELECT * FROM agent_memories
            WHERE {where_clause}
            AND (expires_at IS NULL OR expires_at > NOW())
            ORDER BY importance DESC, last_accessed DESC
            LIMIT :limit
            """
            params["limit"] = limit

            result = db.execute(text(sql_query), params)
            rows = result.fetchall()

            memories = []
            from app.agents.memory import Memory, MemoryType, MemoryImportance

            for row in rows:
                memories.append(Memory(
                    id=row.id,
                    agent_id=row.agent_id,
                    content=row.content,
                    memory_type=MemoryType(row.memory_type),
                    importance=MemoryImportance(row.importance),
                    tags=json.loads(row.tags) if row.tags else [],
                    metadata=json.loads(row.metadata) if row.metadata else {},
                    created_at=row.created_at,
                    last_accessed=row.last_accessed,
                    access_count=row.access_count,
                    expires_at=row.expires_at
                ))

            return memories

        except Exception as e:
            logger.error(f"搜索记忆失败: {e}")
            return []
        finally:
            if db:
                db.close()

    async def delete_memory(self, memory_id: str) -> bool:
        """删除记忆"""
        try:
            db = self.get_db_session()

            result = db.execute(
                text("DELETE FROM agent_memories WHERE id = :id"),
                {"id": memory_id}
            )
            db.commit()

            return result.rowcount > 0

        except Exception as e:
            logger.error(f"删除记忆失败: {e}")
            if db:
                db.rollback()
            return False
        finally:
            if db:
                db.close()


# 全局存储实例
memory_storage = SQLAlchemyMemoryStorage()
