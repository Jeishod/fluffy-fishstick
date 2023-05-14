from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, MetaData, String

from app.db.session import Base
from app.utils.enums import Symbols, TriggerPeriods


# from sqlalchemy.dialects.postgresql import JSONB


metadata = MetaData()


class KucoinTrigger(Base):
    __tablename__ = "kucoin_triggers"
    metadata = metadata

    id: int = Column(Integer, primary_key=True)

    from_symbol: Symbols = Column(String)
    to_symbol: Symbols = Column(String)

    min_value: float = Column(Float)
    max_value: float = Column(Float)
    trigger_count: int = Column(Integer)

    period_seconds: TriggerPeriods = Column(Integer)
    is_active: bool = Column(Boolean, default=False)
    started_at: datetime = Column(DateTime(timezone=False), default=datetime.utcnow)
    cancelled_at: datetime = Column(DateTime(timezone=False))


# class KucoinTransactions(Base):
#     __tablename__ = "kucoin_transactions"
#     metadata = metadata
#     id: int = Column(Integer, primary_key=True)
#     raw_data: dict = Column(JSONB, default=dict)
#     created_at: datetime = Column(DateTime(timezone=False), default=datetime.utcnow)
