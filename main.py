from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def helo():
    return {'message':'hello server'}