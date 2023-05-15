"""update fields names

Revision ID: 697771f5b2ff
Revises: 22201248c0fb
Create Date: 2023-05-15 21:14:06.265873+00:00

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision = "697771f5b2ff"
down_revision = "22201248c0fb"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("kucoin_triggers", sa.Column("min_value_usdt", sa.Float(), nullable=True))
    op.add_column("kucoin_triggers", sa.Column("max_value_usdt", sa.Float(), nullable=True))
    op.add_column("kucoin_triggers", sa.Column("transactions_count", sa.Integer(), nullable=True))
    op.drop_column("kucoin_triggers", "min_value")
    op.drop_column("kucoin_triggers", "cancelled_at")
    op.drop_column("kucoin_triggers", "is_active")
    op.drop_column("kucoin_triggers", "max_value")
    op.drop_column("kucoin_triggers", "trigger_count")
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("kucoin_triggers", sa.Column("trigger_count", sa.INTEGER(), autoincrement=False, nullable=True))
    op.add_column(
        "kucoin_triggers", sa.Column("max_value", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True)
    )
    op.add_column("kucoin_triggers", sa.Column("is_active", sa.BOOLEAN(), autoincrement=False, nullable=True))
    op.add_column(
        "kucoin_triggers", sa.Column("cancelled_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True)
    )
    op.add_column(
        "kucoin_triggers", sa.Column("min_value", sa.DOUBLE_PRECISION(precision=53), autoincrement=False, nullable=True)
    )
    op.drop_column("kucoin_triggers", "transactions_count")
    op.drop_column("kucoin_triggers", "max_value_usdt")
    op.drop_column("kucoin_triggers", "min_value_usdt")
    # ### end Alembic commands ###
