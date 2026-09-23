from typing import List

from fastapi import HTTPException, status

from app.models import Task
from app.repository import TaskRepository


class TaskService:
    """Business rules live here. Depends only on the TaskRepository
    interface, so swapping in-memory -> Postgres never touches this file."""

    def __init__(self, repository: TaskRepository) -> None:
        self._repo = repository

    def list_tasks(self) -> List[Task]:
        return self._repo.list_all()

    def get_task(self, task_id: int) -> Task:
        task = self._repo.get(task_id)
        if task is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        return task

    def create_task(self, title: str) -> Task:
        if not title.strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is empty")
        return self._repo.create(title.strip())

    def update_task(self, task_id: int, title: str | None, done: bool | None) -> Task:
        self.get_task(task_id)  # 404s if missing

        if title is None and done is None:
            raise HTTPException(status_code=400, detail="No data provided for update")

        if title is not None and not title.strip():
            raise HTTPException(status_code=400, detail="Title is empty")

        updated = self._repo.update(task_id, title, done)
        assert updated is not None
        return updated

    def delete_task(self, task_id: int) -> None:
        self.get_task(task_id)  # 404s if missing
        self._repo.delete(task_id)
