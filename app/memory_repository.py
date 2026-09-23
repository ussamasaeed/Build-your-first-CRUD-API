from typing import Dict, List, Optional

from app.models import Task
from app.repository import TaskRepository


class InMemoryTaskRepository(TaskRepository):
    """Stores tasks in a plain dict. Data is lost on restart —
    useful for tests and for the earlier stage of this project."""

    def __init__(self) -> None:
        self._tasks: Dict[int, Task] = {}
        self._next_id = 1

    def list_all(self) -> List[Task]:
        return list(self._tasks.values())

    def get(self, task_id: int) -> Optional[Task]:
        return self._tasks.get(task_id)

    def create(self, title: str) -> Task:
        task = Task(id=self._next_id, title=title, done=False)
        self._tasks[task.id] = task
        self._next_id += 1
        return task

    def update(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[Task]:
        task = self._tasks.get(task_id)
        if task is None:
            return None
        updated = task.model_copy(update={
            k: v for k, v in {"title": title, "done": done}.items() if v is not None
        })
        self._tasks[task_id] = updated
        return updated

    def delete(self, task_id: int) -> bool:
        return self._tasks.pop(task_id, None) is not None
