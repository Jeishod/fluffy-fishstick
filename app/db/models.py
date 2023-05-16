from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, MetaData, String

from app.db.session import Base
from app.utils.enums import Symbols, TriggerPeriods


metadata = MetaData()


class KucoinTrigger(Base):
    __tablename__ = "kucoin_triggers"
    metadata = metadata

    id: int = Column(Integer, primary_key=True)

    from_symbol: Symbols = Column(String)
    to_symbol: Symbols = Column(String)

    min_value_usdt: float = Column(Float)
    max_value_usdt: float = Column(Float)

    transactions_max_count: int = Column(Integer)
    period_seconds: TriggerPeriods = Column(Integer)
    started_at: datetime = Column(DateTime(timezone=False), default=datetime.utcnow)
