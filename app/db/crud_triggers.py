from dataclasses import dataclass
from datetime import datetime

from loguru import logger as LOGGER
from sqlalchemy import exists, select

from app.db.models import KucoinTrigger
from app.db.session import Database
from app.utils.enums import TradeSide, TriggerPeriods


@dataclass
class KucoinTriggersManager:
    db: Database

    async def already_exists(self, from_symbol: str, to_symbol: str) -> bool:
        query = select(exists().where(KucoinTrigger.from_symbol == from_symbol, KucoinTrigger.to_symbol == to_symbol))
        async with self.db.session() as session:
            result = await session.execute(query)
            return result.scalar()

    async def create(
        self,
        from_symbol: str,
        to_symbol: str,
        min_value_usdt: float,
        max_value_usdt: float,
        transactions_max_count: int,
        side: TradeSide,
        period_seconds: TriggerPeriods,
    ) -> KucoinTrigger | None:
        if await self.already_exists(from_symbol=from_symbol, to_symbol=to_symbol):
            LOGGER.debug(f"[DB] Trigger already exists: {from_symbol}-{to_symbol}")
            return None
        new_trigger = KucoinTrigger(
            from_symbol=from_symbol,
            to_symbol=to_symbol,
            min_value_usdt=min_value_usdt,
            max_value_usdt=max_value_usdt,
            transactions_max_count=transactions_max_count,
            side=side,
            period_seconds=period_seconds,
            started_at=datetime.utcnow(),
        )
        async with self.db.session() as session:
            session.add(new_trigger)
            await session.commit()
            await session.refresh(new_trigger)
        return new_trigger

    async def get(self, from_symbol: str, to_symbol: str) -> KucoinTrigger | None:
        query = select(KucoinTrigger).filter_by(from_symbol=from_symbol, to_symbol=to_symbol)
        async with self.db.session() as session:
            result = await session.execute(query)
            return result.scalar()

    async def get_list(self) -> list[KucoinTrigger] | None:
        query = select(KucoinTrigger).order_by(KucoinTrigger.id)
        async with self.db.session() as session:
            result = await session.execute(query)
            return result.scalars().all()

    async def remove(self, from_symbol: str, to_symbol: str) -> KucoinTrigger | None:
        db_trigger = await self.get(from_symbol=from_symbol, to_symbol=to_symbol)
        if db_trigger:
            async with self.db.session() as session:
                await session.delete(db_trigger)
                await session.commit()
        return db_trigger
