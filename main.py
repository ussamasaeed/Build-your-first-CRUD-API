from fastapi import FastAPI, HTTPException, status, Path, Response
import json
from pydantic import BaseModel, Field
from typing import Annotated, Optional
import sqlite3

# Create Database
database = sqlite3.connect("task.db")
database = database.cursor()

# Create tabes
database.execute("""CREATE TABLE IF NOT EXISTS tasks(
    id INTEGER PRIMARY KEY,
    text TEXT,
    done boolen)""")



# Load all data funcation
def load_all_data():
    for row in database.execute("""SELECT * FROM tasks"""):
        print(row)

# Load data from spcefic id
def load_task_data(id: int):
    cursor = database.execute("SELECT * FROM tasks WHERE id = ?", (id,))
    row = cursor.fetchone()
    if row:
        return row
    else : raise HTTPException(status_code=404, detail="Task not found")




# Save data funcation
def save_data(id: int, text: str, done: bool):
    database.execute("INSERT INTO tasks (id, text, done) VALUES (?,?,?)",
                     (id,text,done))

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

# get tasks and task from id
@app.get("/tasks")
def all_tasks():
    data = load_all_data()
    return data

@app.get("/tasks/{id}")
def task(id: int):
    data = load_task_data(id)
    return data

#Stage 3 start
#create pydantic class

class task_create(BaseModel):

    title: str


@app.post("/tasks",status_code=status.HTTP_201_CREATED)
def create_task(task: task_create):
    
    if not task.title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is empty")

    
    cursor = database.execute("SELECT MAX(id) FROM tasks")
    max_id_row = cursor.fetchone()
    
    new_id = (max_id_row[0] if max_id_row and max_id_row[0] is not None else 0) + 1

    
    save_data(id=new_id, text=task.title, done=False)


    return {
        "id": new_id,
        "title": task.title,
        "done": False
    }

# stage 4 start

# pydantic class
class task_update(BaseModel):
    title: Annotated[Optional[str], Field(default=None)]
    done: Annotated[Optional[str], Field(default=None)]

# endpoint for update
@app.put("/task/{id}")
def update_task(id, update: task_update):

    data = load_data()
    update_data_only = update.model_dump(exclude_unset=True)

    for task in data["tasks"]:
        
        if str(task["id"]) == str(id): 
            
            for key, value in update_data_only.items():
                task[key] = value

            save_data(data)
            return {"message": "Task updated successfully", "task": task}

    raise HTTPException(status_code=404, detail="id not found")
    
# Delete task endpoint
@app.delete("/tasks/{id}", status_code=204)
def delete_task(id: int):
    data = load_data()

    for i, task in enumerate(data["tasks"]):
        if task["id"] == id:

            # Remove task
            data["tasks"].pop(i)

            save_data(data)

            # 204 = no response body
            return Response(status_code=204)

    raise HTTPException(
        status_code=404,
        detail="Task not found"
    )
