# Build-your-first-CRUD-API

A FastAPI Task API (Create, Read, Update, Delete) backed by Postgres, with
Docker Compose running the app and the database together. `/docs` has the
interactive API documentation.

## Architecture

```
app/
  models.py               # Task, TaskCreate, TaskUpdate (Pydantic)
  repository.py            # TaskRepository — the interface
  memory_repository.py     # in-memory implementation (no persistence)
  postgres_repository.py   # Postgres implementation (persists)
  service.py                # business rules — depends only on TaskRepository
  routes.py                  # HTTP endpoints — depends only on TaskService
  dependencies.py            # wires the Postgres repository into the service
main.py                      # creates the FastAPI app, mounts the routes
db/init.sql                  # creates the tasks table on first container start
```

The service and routes only ever talk to the `TaskRepository` interface —
they have no idea whether they're backed by memory or Postgres. Swapping
`InMemoryTaskRepository` for `PostgresTaskRepository` in
`app/dependencies.py` is the only change needed to move from one to the other.

## 1. Start Postgres in Docker (standalone, with a persistent volume)

```bash
docker run -d \
  --name task-db \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=task_db \
  -p 5432:5432 \
  -v pgdata:/var/lib/postgresql/data \
  postgres:16
```

The `-v pgdata:/var/lib/postgresql/data` volume is what makes the data
survive a container restart or removal — without it, deleting the
container deletes the data too.

## 2. Configure the connection string

Copy the template and fill it in:

```bash
cp .env.example .env
```

`.env` is gitignored (see `.gitignore`) so credentials never get committed;
`.env.example` is the checked-in template teammates copy from.

## 3. Create the table

`db/init.sql` has the schema:

```sql
CREATE TABLE IF NOT EXISTS tasks (
    id    SERIAL PRIMARY KEY,
    title TEXT NOT NULL,
    done  BOOLEAN NOT NULL DEFAULT false
);
```

Run it against the container from step 1:

```bash
docker exec -i task-db psql -U postgres -d task_db < db/init.sql
```

(When you use `docker compose up` instead — step 5 — this file is mounted
into Postgres's `/docker-entrypoint-initdb.d/`, so it runs automatically the
first time the `db` volume is created.)

## 4. Run the app against Postgres

```bash
pip install -r requirements.txt
uvicorn main:app --reload
```

`app/postgres_repository.py` implements the same `TaskRepository` interface
as `app/memory_repository.py` — `app/service.py` and `app/routes.py` are
untouched by the swap; only `app/dependencies.py` picks which repository to
construct.

## 5. Run the whole stack with Docker Compose

```bash
docker compose up
```

This starts `db` (Postgres, with the same named volume so its data
persists across `docker compose down` / `up`) and `app` (this API), wired
together with `DATABASE_URL` pointing at the `db` service. The API is at
`http://localhost:8000`, docs at `http://localhost:8000/docs`.

## 6. Prove persistence

```bash
# with the stack up, create some tasks
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"buy milk"}'
curl -X POST localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"write report"}'
curl localhost:8000/tasks   # -> both tasks

# restart everything — app container AND db container
docker compose restart

# check again
curl localhost:8000/tasks   # -> the same two tasks, still there
```

You can go further and prove it survives a full teardown (not just a
restart), as long as you don't remove the volume:

```bash
docker compose down     # stops and removes containers, volume stays
docker compose up -d    # fresh containers, same volume
curl localhost:8000/tasks   # -> tasks are still there
```

Only `docker compose down -v` (which explicitly removes volumes) or `docker
volume rm pgdata` would wipe the data — that's the volume doing its job.

## Endpoints

| Method | Path         | Description       |
|--------|--------------|--------------------|
| GET    | `/tasks`     | list all tasks     |
| GET    | `/tasks/{id}`| get one task       |
| POST   | `/tasks`     | create a task      |
| PUT    | `/tasks/{id}`| update a task      |
| DELETE | `/tasks/{id}`| delete a task       |
