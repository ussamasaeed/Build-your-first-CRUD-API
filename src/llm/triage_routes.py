import os

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from app.llm.schema import TriageInput, TriageOutput

router = APIRouter()


@router.post("/triage", response_model=TriageOutput)
async def triage(request: Request):
    # Parse JSON without allowing FastAPI's default 422 response.
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid request",
                "field": "body",
                "message": "Request body must be valid JSON",
            },
        )

    # Validate before doing anything involving a model.
    try:
        data = TriageInput.model_validate(body)
    except ValidationError as exc:
        first_error = exc.errors()[0]
        location = first_error["loc"]
        field = str(location[0]) if location else "body"

        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid request",
                "field": field,
                "message": first_error["msg"],
            },
        )
    except (TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid request",
                "field": "body",
                "message": "Request body must be a JSON object",
            },
        )

    # Stage 1: never call a model.
    if os.getenv("LLM_STUB") == "1":
        result = TriageOutput(
            category="other",
            urgency="normal",
            confidence=0.5,
            reason="Stub response for endpoint testing.",
        )
        return result

    return JSONResponse(
        status_code=503,
        content={
            "error": "Model is not configured for this stage"
        },
    )