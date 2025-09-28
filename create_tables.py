#!/usr/bin/env python3
"""Create document tables directly"""

import asyncio
import asyncpg
import os

async def create_tables():
    # 从环境变量获取数据库连接信息
    DATABASE_URL = "postgresql://postgres:password@localhost:5432/flyfly_db"

    # 连接数据库
    conn = await asyncpg.connect(DATABASE_URL)

    try:
        # 创建 documents 表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id VARCHAR(255) UNIQUE NOT NULL,
                file_name VARCHAR(255) NOT NULL,
                file_path TEXT,
                file_size BIGINT,
                content_type VARCHAR(100),
                chunks_count INTEGER DEFAULT 0,
                processing_status VARCHAR(50) DEFAULT 'pending',
                user_id UUID NOT NULL REFERENCES users(id),
                document_metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                processed_at TIMESTAMPTZ
            );
        """)

        # 创建索引
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_documents_document_id ON documents(document_id);
        """)

        # 创建 document_chunks 表
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                chunk_index INTEGER NOT NULL,
                content TEXT NOT NULL,
                content_preview TEXT,
                chroma_id VARCHAR(255),
                chunk_metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
        """)

        # 创建索引
        await conn.execute("""
            CREATE INDEX IF NOT EXISTS ix_document_chunks_chroma_id ON document_chunks(chroma_id);
        """)

        print("✅ Document tables created successfully!")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(create_tables())