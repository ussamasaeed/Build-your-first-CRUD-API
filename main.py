from fastapi import FastAPI, HTTPException, status
import json
from pydantic import BaseModel

# Load data funcation
def load_data():
    with open("data.json", "r") as f:
        return json.load(f)

# Save data funcation
def save_data(data):
    with open("data.json","w") as f:
        json.dump(data,f)

app = FastAPI()

# @app.get("/")
# def helo():
#     return {'message':'hello server'}


@app.get("/")
def read_root():
    return{
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"]
    }

@app.get("/health")
def read_health():
    return{
        "status": "ok"
    }

# @app.get("/tasks")
# def all_tasks():
#     data = load_data()
#     return data

@app.get("/tasks/{id}")
def task(id: int):
    data = load_data()

    for task in data["tasks"]:
        if task["id"] == id:
            return task

        else : raise HTTPException(status_code=404, detail="Task not found")

# Stage 3 start
# create pydantic class

class task_create(BaseModel):

    title: str


@app.post("/tasks",status_code=status.HTTP_201_CREATED)
def create_task(task: task_create):

    data = load_data()

    if not task.title.strip():

        raise HTTPException(status_code=400,detail="title is empty")

    new_id = max((t["id"] for t in data["tasks"]), default=0)+1

    new_task = {
        "id": new_id,
        "title": task.title,
        "done": False
    }

    data["tasks"].append(new_task)

    save_data(data)

