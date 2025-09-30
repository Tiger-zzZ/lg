"""Mark existing tables as migrated

Revision ID: a1b2c3d4e5f6
Revises: 8c188c0aa681
Create Date: 2025-09-28 17:04:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = '8c188c0aa681'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 表已经存在，这个迁移只是为了标记状态
    # 检查并确保必要的扩展存在
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    pass


def downgrade() -> None:
    # 不执行任何操作，因为表是手动创建的
    pass