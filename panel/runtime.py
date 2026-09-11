import asyncio
import threading
from collections.abc import Awaitable
from collections.abc import Callable
from typing import override

import streamlit as st
from poltergeist_core.adapters import boomlings
from poltergeist_core.adapters import mysql
from poltergeist_core.adapters import redis
from poltergeist_core.adapters import storage
from poltergeist_core.adapters.boomlings import BoomlingsClient
from poltergeist_core.adapters.mysql import ImplementsMySQL
from poltergeist_core.adapters.mysql import MySQLPool
from poltergeist_core.adapters.redis import RedisClient
from poltergeist_core.adapters.storage import ImplementsStorage
from poltergeist_core.services import AbstractContext
from poltergeist_core.utilities import logging

type Action[T] = Callable[[AbstractContext], Awaitable[T]]

logger = logging.get_logger(__name__)


class PanelContext(AbstractContext):
    """One transaction per panel action, committed when the action returns."""

    __slots__ = (
        "_boomlings_client",
        "_redis_client",
        "_storage_backend",
        "_transaction",
    )

    def __init__(
        self,
        transaction: ImplementsMySQL,
        redis_client: RedisClient,
        storage_backend: ImplementsStorage,
        boomlings_client: BoomlingsClient,
    ) -> None:
        self._transaction = transaction
        self._redis_client = redis_client
        self._storage_backend = storage_backend
        self._boomlings_client = boomlings_client

    @property
    @override
    def _mysql(self) -> ImplementsMySQL:
        return self._transaction

    @property
    @override
    def _redis(self) -> RedisClient:
        return self._redis_client

    @property
    @override
    def storage(self) -> ImplementsStorage:
        return self._storage_backend

    @property
    @override
    def boomlings(self) -> BoomlingsClient:
        return self._boomlings_client


class Runtime:
    """Owns the adapters on a background event loop so the synchronous
    Streamlit script can call the asynchronous service layer. Every `run` is
    its own transaction."""

    def __init__(self) -> None:
        self._loop = asyncio.new_event_loop()
        self._pool: MySQLPool = mysql.default()
        self._redis: RedisClient = redis.default()
        self._storage = storage.default()
        self._boomlings = boomlings.default()
        self._thread = threading.Thread(
            target=self._loop.run_forever, name="panel-runtime", daemon=True
        )
        self._thread.start()
        self._await(self._connect())

    async def _connect(self) -> None:
        await self._pool.connect()
        await self._redis.initialise()
        logger.info("Panel runtime connected to the databases.")

    def _await[T](self, awaitable: Awaitable[T]) -> T:
        future = asyncio.run_coroutine_threadsafe(self._wrap(awaitable), self._loop)

        return future.result()

    @staticmethod
    async def _wrap[T](awaitable: Awaitable[T]) -> T:
        return await awaitable

    async def _transact[T](self, action: Action[T]) -> T:
        async with self._pool.transaction() as transaction:
            return await action(
                PanelContext(transaction, self._redis, self._storage, self._boomlings)
            )

    def run[T](self, action: Action[T]) -> T:
        return self._await(self._transact(action))


@st.cache_resource(show_spinner="Connecting to the databases…")
def active() -> Runtime:
    return Runtime()
