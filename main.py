try:
    from dotenv import load_dotenv  # type: ignore[reportMissingImports]
except ModuleNotFoundError:  # pragma: no cover
    def load_dotenv(*_args, **_kwargs):
        return False

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

load_dotenv()  # reads .env into os.environ before anything else touches it

from app.access_routes import router as access_router  # noqa: E402
from app.auth_guard import Unauthorized, unauthorized_handler  # noqa: E402
from app.auth_routes import router as auth_router  # noqa: E402
from app.routes import router  # noqa: E402  (import after load_dotenv on purpose)

app = FastAPI(title="Task API")
app.add_exception_handler(Unauthorized, unauthorized_handler)
app.include_router(router)
app.include_router(auth_router)
app.include_router(access_router)
app.mount("/static", StaticFiles(directory="static"), name="static")
