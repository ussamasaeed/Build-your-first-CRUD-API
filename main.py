from fastapi import FastAPI, HTTPException
import json

def load_data():
    with open("data.json", "r") as f:
        return json.load(f)

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

@app.get("/tasks")
def all_tasks():
    data = load_data()
    return data

@app.get("/tasks/{id}")
def task(id: int):
    data = load_data()

    for task in data["tasks"]:
        if task["id"] == id:
            return task

        else : raise HTTPException(status_code=404, detail="Task not found")