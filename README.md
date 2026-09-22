<img width="1920" height="1080" alt="Screenshot (57)" src="https://github.com/user-attachments/assets/d1b54974-805a-4d04-81c6-52da1a101ed2" />
# Build-your-first-CRUD-API
This is FastAPI
in which we create operation Create, Read Update and Delete
And /docs in available its documentation
### Installation
first create venv in python
then actvate it
install "pip install fastapi uvicorn pydantic
now this time to run this api

how we run this project
    uvicorn main:app --reload

why we chose sqlite ?
    beasuse its lite weight and fast and easy to use

where store database
    this time store in local directory

Example of sqlite3 qurey in python
    import sqlite3

    # Connect to database
    connection = sqlite3.connect("task.db")
    cursor = connection.cursor()

    # Execute SQL query
    cursor.execute(
        "SELECT * FROM tasks WHERE id = ?",
        (1,)
    )

    # Get result
    task = cursor.fetchone()

    print(task)

    # Close connection
    connection.close()
