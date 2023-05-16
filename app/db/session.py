from asyncio import current_task
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from loguru import logger as LOGGER
from sqlalchemy import MetaData, text
from sqlalchemy.ext.asyncio import AsyncSession, async_scoped_session, async_sessionmaker, create_async_engine
from sqlalchemy.orm import as_declarative, declared_attr


metadata = MetaData()


@as_declarative()
class Base:
    class Meta:
        metadata = metadata

    id: Any
    __name__: str

    @declared_attr
    def __tablename__(cls) -> str:
        return cls.__name__.lower()


class Database:
    def __init__(self, url: str, echo: bool = False) -> None:
        self._engine = create_async_engine(url=url, echo=echo)
        self._async_session_factory = async_scoped_session(
            async_sessionmaker(
                bind=self._engine,
                class_=AsyncSession,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            ),
            scopefunc=current_task,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        session: AsyncSession = self._async_session_factory()
        try:
            yield session
        except Exception:
            LOGGER.error("[DB] Session rollback because of exception")
            await session.rollback()
            raise
        finally:
            await session.close()
            await self._async_session_factory.remove()

    async def ping(self) -> bool:
        try:
            async with self.session() as session:
                LOGGER.debug("[DB] Ping...")
                await session.execute(text("SELECT 1"))
                LOGGER.debug("[DB] Ping... Success!")
                return True

        except Exception as e:
            LOGGER.error(f"[DB] Testing database connection... Failed: {e}")
            return False

    async def disconnect(self) -> None:
        await self._engine.dispose()
