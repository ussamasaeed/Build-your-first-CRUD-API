from typing import List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from app.models import Task
from app.repository import TaskRepository


class PostgresTaskRepository(TaskRepository):
    """Same interface as InMemoryTaskRepository, backed by Postgres.
    The service and routes that use TaskRepository don't change at all —
    only this class, and which one gets wired up in main.py."""

    def __init__(self, dsn: str) -> None:
        self._dsn = dsn
        self._conn = psycopg2.connect(dsn)
        self._conn.autocommit = True

    def _row_to_task(self, row: dict) -> Task:
        return Task(id=row["id"], title=row["title"], done=row["done"])

    def list_all(self) -> List[Task]:
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, title, done FROM tasks ORDER BY id")
            return [self._row_to_task(r) for r in cur.fetchall()]

    def get(self, task_id: int) -> Optional[Task]:
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            return self._row_to_task(row) if row else None

    def create(self, title: str) -> Task:
        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, false) "
                "RETURNING id, title, done",
                (title,),
            )
            return self._row_to_task(cur.fetchone())

    def update(self, task_id: int, title: Optional[str], done: Optional[bool]) -> Optional[Task]:
        if title is None and done is None:
            return self.get(task_id)

        with self._conn.cursor(cursor_factory=RealDictCursor) as cur:
            if title is not None:
                cur.execute("UPDATE tasks SET title = %s WHERE id = %s", (title, task_id))
            if done is not None:
                cur.execute("UPDATE tasks SET done = %s WHERE id = %s", (done, task_id))
            cur.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
            row = cur.fetchone()
            return self._row_to_task(row) if row else None

    def delete(self, task_id: int) -> bool:
        with self._conn.cursor() as cur:
            cur.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            return cur.rowcount > 0
