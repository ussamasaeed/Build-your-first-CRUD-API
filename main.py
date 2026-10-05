try:
    from dotenv import load_dotenv  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):
        return False

from fastapi import FastAPI

load_dotenv()  # reads .env into os.environ before anything else touches it

from app.routes import router  # noqa: E402  (import after load_dotenv on purpose)

app = FastAPI(title="Task API")
app.include_router(router)
