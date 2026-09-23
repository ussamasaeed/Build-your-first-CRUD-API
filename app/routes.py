from fastapi import APIRouter, Depends, Response, status

from app.dependencies import get_service
from app.models import Task, TaskCreate, TaskUpdate
from app.service import TaskService

router = APIRouter()


@router.get("/")
def read_root():
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }


@router.get("/health")
def read_health():
    return {"status": "ok"}


@router.get("/tasks", response_model=list[Task])
def list_tasks(service: TaskService = Depends(get_service)):
    return service.list_tasks()


@router.get("/tasks/{id}", response_model=Task)
def get_task(id: int, service: TaskService = Depends(get_service)):
    return service.get_task(id)


@router.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(task: TaskCreate, service: TaskService = Depends(get_service)):
    return service.create_task(task.title)


@router.put("/tasks/{id}", response_model=Task)
def update_task(id: int, update: TaskUpdate, service: TaskService = Depends(get_service)):
    return service.update_task(id, update.title, update.done)


@router.delete("/tasks/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(id: int, service: TaskService = Depends(get_service)):
    service.delete_task(id)
    return Response(status_code=204)
