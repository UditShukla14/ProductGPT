from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from neo4j import GraphDatabase, Driver, Session

from app.config import settings


class Neo4jClient:
    def __init__(self) -> None:
        self._driver: Driver | None = None

    @property
    def enabled(self) -> bool:
        return settings.neo4j_enabled

    def connect(self) -> bool:
        if not self.enabled:
            return False
        if self._driver is not None:
            return True
        try:
            self._driver = GraphDatabase.driver(
                settings.neo4j_uri,
                auth=(settings.neo4j_user, settings.neo4j_password),
            )
            self._driver.verify_connectivity()
            return True
        except Exception:
            if self._driver is not None:
                self._driver.close()
                self._driver = None
            return False

    def close(self) -> None:
        if self._driver is not None:
            self._driver.close()
            self._driver = None

    @property
    def is_connected(self) -> bool:
        return self._driver is not None

    @contextmanager
    def session(self) -> Iterator[Session]:
        if self._driver is None:
            raise RuntimeError("Neo4j is not connected")
        session = self._driver.session(database=settings.neo4j_database)
        try:
            yield session
        finally:
            session.close()


neo4j_client = Neo4jClient()
