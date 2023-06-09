"""add_trigger__side

Revision ID: ba092c65fbd8
Revises: 1aaece15756a
Create Date: 2023-05-23 14:03:02.654784+00:00

"""
import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "ba092c65fbd8"
down_revision = "1aaece15756a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column("kucoin_triggers", sa.Column("side", sa.String(), nullable=True))
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column("kucoin_triggers", "side")
    # ### end Alembic commands ###
