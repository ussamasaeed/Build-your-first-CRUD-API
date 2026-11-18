
import asyncio
import json
import logging
import os
import random
import time

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openai import AsyncOpenAI, APIStatusError, APITimeoutError
from pydantic import ValidationError

from app.llm.output import parse_and_validate
from app.llm.quarantine import save_failed_output
from app.llm.schema import TriageInput, TriageOutput


router = APIRouter()

logger = logging.getLogger("app.llm")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILE = PROJECT_ROOT / "prompts" / "triage-v1.md"
PROMPT_VERSION = "triage-v1"

# One initial request plus at most three retries.
MAX_RETRIES = 3

# Exponential backoff delays: 1, 2, 4 seconds.
BACKOFF_DELAYS = [1, 2, 4]


def log_event(event: dict) -> None:
    """Write one structured JSON log line to stdout."""
    logger.info(json.dumps(event, ensure_ascii=False))


def get_retry_after_seconds(exc: APIStatusError):
    """Read Retry-After from the provider response, if available."""

    retry_after = exc.response.headers.get("retry-after")

    if not retry_after:
        return None

    # Retry-After may be a number of seconds.
    try:
        return max(0.0, float(retry_after))
    except ValueError:
        pass

    # It may alternatively be an HTTP date.
    try:
        retry_date = parsedate_to_datetime(retry_after)

        if retry_date.tzinfo is None:
            retry_date = retry_date.replace(tzinfo=timezone.utc)

        seconds = (
            retry_date - datetime.now(timezone.utc)
        ).total_seconds()

        return max(0.0, seconds)

    except (TypeError, ValueError, OverflowError):
        return None


def get_model_name() -> str:
    return os.getenv("LLM_MODEL", "unknown")


def log_call_result(
    result: dict,
    repair_needed: bool,
    repair_attempt: bool,
) -> None:
    """Log token usage and duration for a successful model response."""

    usage = result.get("usage")

    input_tokens = (
        usage.prompt_tokens if usage else None
    )

    output_tokens = (
        usage.completion_tokens if usage else None
    )

    log_event({
        "event": "llm_call",
        "prompt_version": PROMPT_VERSION,
        "model": get_model_name(),
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "duration_ms": result["duration_ms"],
        "repair_needed": repair_needed,
        "repair_attempt": repair_attempt,
        "status": "success",
    })


async def call_model(
    messages: list[dict],
    repair_attempt: bool = False,
) -> dict:
    """
    Call the model with a 30-second timeout.

    Retry only:
    - Timeouts
    - HTTP 429
    - HTTP 5xx

    SDK automatic retries are disabled. This function owns
    the retry policy.
    """

    client = AsyncOpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
        timeout=30.0,
        max_retries=0,
    )

    try:
        for attempt in range(MAX_RETRIES + 1):

            started_at = time.perf_counter()

            try:
                response = await client.chat.completions.create(
                    model=os.environ["LLM_MODEL"],
                    messages=messages,
                    temperature=0,
                )

                duration_ms = round(
                    (time.perf_counter() - started_at) * 1000
                )

                content = response.choices[0].message.content

                if not isinstance(content, str) or not content.strip():
                    raise ValueError("Model returned empty output")

                return {
                    "content": content,
                    "usage": response.usage,
                    "duration_ms": duration_ms,
                }

            except (APITimeoutError, APIStatusError) as exc:

                duration_ms = round(
                    (time.perf_counter() - started_at) * 1000
                )

                is_timeout = isinstance(exc, APITimeoutError)

                status_code = (
                    None if is_timeout else exc.status_code
                )

                retryable = (
                    is_timeout
                    or status_code == 429
                    or (
                        status_code is not None
                        and status_code >= 500
                    )
                )

                log_event({
                    "event": "llm_call",
                    "prompt_version": PROMPT_VERSION,
                    "model": get_model_name(),
                    "input_tokens": None,
                    "output_tokens": None,
                    "duration_ms": duration_ms,
                    "repair_needed": None,
                    "repair_attempt": repair_attempt,
                    "status": "failed",
                    "status_code": status_code,
                    "timeout": is_timeout,
                    "retry_attempt": attempt,
                })

                # Never retry 400, 401, 403, or other non-retryable errors.
                if not retryable or attempt >= MAX_RETRIES:
                    raise

                # Respect Retry-After for HTTP 429.
                delay = None

                if status_code == 429:
                    delay = get_retry_after_seconds(exc)

                # Otherwise use exponential backoff with jitter.
                if delay is None:
                    delay = (
                        BACKOFF_DELAYS[attempt]
                        + random.uniform(0, 0.25)
                    )

                await asyncio.sleep(delay)

        raise RuntimeError("Model retry loop ended unexpectedly")

    finally:
        await client.close()


def model_error_response(exc: Exception) -> JSONResponse:
    """Convert provider failures into safe HTTP responses."""

    if isinstance(exc, APITimeoutError):
        return JSONResponse(
            status_code=504,
            content={
                "error": "Model request timed out",
                "message": "The model did not respond within 30 seconds.",
            },
        )

    if isinstance(exc, APIStatusError):
        status_code = exc.status_code

        if status_code == 401:
            message = (
                "The model provider rejected the API key. "
                "Check LLM_API_KEY."
            )
        elif status_code == 403:
            message = "The model provider denied this request."
        elif status_code == 400:
            message = "The model provider rejected the request."
        elif status_code == 429:
            message = "The model provider rate limit was reached."
        else:
            message = "The model provider returned an error."

        return JSONResponse(
            status_code=502,
            content={
                "error": "Model provider error",
                "message": message,
                "provider_status": status_code,
            },
        )

    return JSONResponse(
        status_code=502,
        content={
            "error": "Model request failed",
            "message": "The model provider could not complete the request.",
        },
    )


async def run_triage(data: TriageInput):
    """Run triage using the kill switch, stub, or real model."""

    # Stage 4: Kill switch. This takes priority over stub/model mode.
    if os.getenv("LLM_ENABLED", "true").lower() == "false":
        return TriageOutput(
            category="other",
            urgency="normal",
            confidence=0.0,
            reason="AI triage is currently disabled.",
        )

    # Stage 1: Stub mode. No model calls.
    if os.getenv("LLM_STUB") == "1":
        return TriageOutput(
            category="other",
            urgency="normal",
            confidence=0.5,
            reason="Stub response for endpoint testing.",
        )

    # Load the versioned system prompt.
    try:
        system_prompt = PROMPT_FILE.read_text(encoding="utf-8")
    except OSError:
        return JSONResponse(
            status_code=500,
            content={
                "error": "Prompt file could not be loaded",
                "prompt_version": PROMPT_VERSION,
            },
        )

    # Keep untrusted input separate from the system prompt.
    input_data = {"text": data.text}

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": json.dumps(
                input_data,
                ensure_ascii=False,
            ),
        },
    ]

    # First model call, including controlled network retries.
    try:
        first_result = await call_model(messages)

    except Exception as exc:
        logger.exception("Initial model request failed")
        return model_error_response(exc)

    raw_output = first_result["content"]

    # Parse and validate the first response.
    try:
        validated = parse_and_validate(raw_output)

        log_call_result(
            first_result,
            repair_needed=False,
            repair_attempt=False,
        )

        return validated

    except (ValueError, ValidationError) as first_error:
        first_error_text = str(first_error)

        log_call_result(
            first_result,
            repair_needed=True,
            repair_attempt=False,
        )

    # Exactly one repair attempt.
    repair_payload = {
        "previous_output": raw_output,
        "validation_error": first_error_text,
        "instruction": (
            "Your previous answer was rejected for this reason. "
            "Return only corrected JSON matching the schema."
        ),
    }

    repair_messages = messages + [
        {
            "role": "assistant",
            "content": raw_output,
        },
        {
            "role": "user",
            "content": json.dumps(
                repair_payload,
                ensure_ascii=False,
            ),
        },
    ]

    try:
        repair_result = await call_model(
            repair_messages,
            repair_attempt=True,
        )

    except Exception as exc:
        logger.exception("Model repair request failed")
        return model_error_response(exc)

    repaired_output = repair_result["content"]

    # Validate the repaired response.
    try:
        validated = parse_and_validate(repaired_output)

        log_call_result(
            repair_result,
            repair_needed=True,
            repair_attempt=True,
        )

        return validated

    except (ValueError, ValidationError) as second_error:

        log_call_result(
            repair_result,
            repair_needed=True,
            repair_attempt=True,
        )

        # Both attempts failed: quarantine the response.
        save_failed_output(
            input_data=input_data,
            raw_output=repaired_output,
            error=(
                f"First attempt: {first_error_text}; "
                f"Repair attempt: {str(second_error)}"
            ),
            prompt_version=PROMPT_VERSION,
        )

        return JSONResponse(
            status_code=422,
            content={
                "error": "Model output could not be validated",
                "message": (
                    "The model response failed schema validation "
                    "after one repair attempt."
                ),
            },
        )


@router.post("/triage", response_model=TriageOutput)
async def triage(request: Request):

    # Parse incoming JSON.
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

    # Body must be a JSON object.
    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid request",
                "field": "body",
                "message": "Request body must be a JSON object",
            },
        )

    # Validate input before any model call.
    try:
        data = TriageInput.model_validate(body)

    except ValidationError as exc:
        first_error = exc.errors()[0]
        location = first_error.get("loc", ())
        field = str(location[0]) if location else "body"

        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid request",
                "field": field,
                "message": first_error["msg"],
            },
        )

    return await run_triage(data)
