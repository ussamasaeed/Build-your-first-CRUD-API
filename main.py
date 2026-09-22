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

    title: Annotated[
        Optional[str],
        Field(default=None)
    ]

    done: Annotated[
        Optional[bool],
        Field(default=None)
    ]


@app.put("/tasks/{id}")
def update_task(
    id: int,
    update: task_update
):

    # First check whether task exists
    load_task_data(id)

    # Get only fields that were actually provided
    update_data_only = update.model_dump(
        exclude_unset=True
    )

    # No data provided
    if not update_data_only:

        raise HTTPException(
            status_code=400,
            detail="No data provided for update"
        )

    
    # Update title
    

    if "title" in update_data_only:

        title = update_data_only["title"]

        if not title.strip():

            raise HTTPException(
                status_code=400,
                detail="Title is empty"
            )

        database.execute(
            """
            UPDATE tasks
            SET text = ?
            WHERE id = ?
            """,
            (title, id)
        )

    
    # Update done
    

    if "done" in update_data_only:

        done = update_data_only["done"]

        database.execute(
            """
            UPDATE tasks
            SET done = ?
            WHERE id = ?
            """,
            (done, id)
        )

    # Save changes
    database.connection.commit()

    # Get updated task
    updated_task = load_task_data(id)

    return {
        "message": "Task updated successfully",
        "task": updated_task
    }



# DELETE TASK


@app.delete(
    "/tasks/{id}",
    status_code=status.HTTP_204_NO_CONTENT
)
def delete_task(id: int):

    # Check whether task exists
    load_task_data(id)

    # Delete task from SQLite
    database.execute(
        """
        DELETE FROM tasks
        WHERE id = ?
        """,
        (id,)
    )

    # Save changes
    database.connection.commit()

    # 204 means no response body
    return Response(status_code=204)


# SELECT * FROM tasks;
# SELECT * FROM tasks WHERE done = 1;
# SELECT COUNT(*) FROM tasks;
# UPDATE tasks SET done = 1;
# DELETE FROM tasks WHERE done = 1;