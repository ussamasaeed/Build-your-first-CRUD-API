import os
from functools import lru_cache

from app.postgres_repository import PostgresTaskRepository
from app.repository import TaskRepository
from app.service import TaskService

# Loaded once, reused for every request.
_repository: TaskRepository | None = None


def get_repository() -> TaskRepository:
    global _repository
    if _repository is None:
        dsn = os.environ.get("DATABASE_URL")
        if not dsn:
            raise RuntimeError(
                "DATABASE_URL is not set. Copy .env.example to .env and fill it in."
            )
        _repository = PostgresTaskRepository(dsn)
    return _repository


def get_service() -> TaskService:
    return TaskService(get_repository())
