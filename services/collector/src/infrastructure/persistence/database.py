"""Database connection management."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

logger = structlog.get_logger(__name__)

# Global database instance
_database: Database | None = None


class Database:
    """Manages database connections and sessions."""

    def __init__(
        self,
        url: str,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        self._url = url
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None
        self._echo = echo
        self._pool_size = pool_size
        self._max_overflow = max_overflow

    async def connect(self) -> None:
        """Initialize the database connection."""
        if self._engine is not None:
            return

        logger.info("Connecting to database")

        self._engine = create_async_engine(
            self._url,
            echo=self._echo,
            pool_size=self._pool_size,
            max_overflow=self._max_overflow,
            pool_pre_ping=True,  # Check connection health
        )

        self._session_factory = async_sessionmaker(
            bind=self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )

        logger.info("Database connection established")

    async def disconnect(self) -> None:
        """Close the database connection."""
        if self._engine is None:
            return

        logger.info("Disconnecting from database")
        await self._engine.dispose()
        self._engine = None
        self._session_factory = None
        logger.info("Database connection closed")

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session context manager."""
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    @asynccontextmanager
    async def transaction(self) -> AsyncGenerator[AsyncSession, None]:
        """Get a database session with transaction management."""
        if self._session_factory is None:
            raise RuntimeError("Database not connected. Call connect() first.")

        async with self._session_factory() as session:
            async with session.begin():
                yield session

    @property
    def engine(self) -> AsyncEngine:
        """Get the database engine."""
        if self._engine is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return self._engine

    @property
    def is_connected(self) -> bool:
        """Check if database is connected."""
        return self._engine is not None


def get_database() -> Database:
    """Get the global database instance."""
    global _database
    if _database is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    return _database


def init_database(
    url: str,
    echo: bool = False,
    pool_size: int = 5,
    max_overflow: int = 10,
) -> Database:
    """Initialize the global database instance."""
    global _database
    _database = Database(
        url=url,
        echo=echo,
        pool_size=pool_size,
        max_overflow=max_overflow,
    )
    return _database
