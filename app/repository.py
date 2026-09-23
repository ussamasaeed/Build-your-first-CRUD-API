from abc import ABC, abstractmethod
from typing import List, Optional

from app.models import Task


class TaskRepository(ABC):
    """
    The contract the service layer depends on. Any storage backend
    (in-memory, Postgres, ...) implements this — the service and
    routes never know or care which one is plugged in.
    """

    @abstractmethod
    def list_all(self) -> List[Task]:
        ...

    @abstractmethod
    def get(self, task_id: int) -> Optional[Task]:
        ...

    @abstractmethod
    def create(self, title: str) -> Task:
        ...

    @abstractmethod
    def update(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[Task]:
        ...

    @abstractmethod
    def delete(self, task_id: int) -> bool:
        ...
