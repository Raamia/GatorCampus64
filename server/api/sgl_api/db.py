"""psycopg 3 connection pool + schema application.

Plain SQL rather than an ORM: schema.sql is shared verbatim with the worker, and the parts that
matter (FOR UPDATE SKIP LOCKED, advisory locks, the slot functions) are SQL anyway, so a model
layer would only be a second copy of the schema that can drift.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema.sql"


class Database:
    def __init__(self, url: str, min_size: int = 1, max_size: int = 10):
        self.pool = ConnectionPool(url, min_size=min_size, max_size=max_size, open=True,
                                   kwargs={"row_factory": dict_row})

    @contextmanager
    def tx(self) -> Iterator[psycopg.Connection]:
        """One transaction: commits on success, rolls back on exception."""
        with self.pool.connection() as conn:
            with conn.transaction():
                yield conn

    def close(self) -> None:
        self.pool.close()


def apply_schema(url: str) -> None:
    sql = SCHEMA_PATH.read_text()
    with psycopg.connect(url, autocommit=True) as conn:
        conn.execute("SELECT pg_advisory_lock(hashtext('sgl_schema'))")
        try:
            conn.execute(sql)
        finally:
            conn.execute("SELECT pg_advisory_unlock(hashtext('sgl_schema'))")
