
import json
import os
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from openai import OpenAI
from pydantic import ValidationError

from app.llm.output import parse_and_validate
from app.llm.quarantine import save_failed_output
from app.llm.schema import TriageInput, TriageOutput


router = APIRouter()

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROMPT_FILE = PROJECT_ROOT / "prompts" / "triage-v1.md"
PROMPT_VERSION = "triage-v1"


def call_model(messages: list[dict]) -> str:
    """
    Send messages to the configured OpenAI-compatible model.
    Returns the model's text response.
    """

    client = OpenAI(
        base_url=os.environ["LLM_BASE_URL"],
        api_key=os.environ["LLM_API_KEY"],
    )

    response = client.chat.completions.create(
        model=os.environ["LLM_MODEL"],
        messages=messages,
        temperature=0,
    )

    content = response.choices[0].message.content

    if not isinstance(content, str) or not content.strip():
        raise ValueError("Model returned empty output")

    return content


async def run_triage(data: TriageInput):
    """
    Run triage using stub mode or a real model.

    Real model output must pass JSON parsing and Pydantic
    validation. If it fails, one repair attempt is allowed.
    """

    # Stage 1: Stub mode makes zero model calls.
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

    # Keep user input separate from the system prompt.
    input_data = {"text": data.text}
    user_message = json.dumps(input_data, ensure_ascii=False)

    messages = [
        {
            "role": "system",
            "content": system_prompt,
        },
        {
            "role": "user",
            "content": user_message,
        },
    ]

    # First model attempt.
    try:
        raw_output = call_model(messages)
    except Exception:
        return JSONResponse(
            status_code=502,
            content={
                "error": "The model request failed",
            },
        )

    # Parse and validate the first response.
    try:
        return parse_and_validate(raw_output)

    except (ValueError, ValidationError) as first_error:
        first_error_text = str(first_error)

    # One repair attempt only.
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

    # Make exactly one repair call.
    try:
        repaired_output = call_model(repair_messages)
    except Exception:
        return JSONResponse(
            status_code=502,
            content={
                "error": "The model repair request failed",
            },
        )

    # Validate the repaired response.
    try:
        return parse_and_validate(repaired_output)

    except (ValueError, ValidationError) as second_error:

        # Both attempts failed. Save the failure for investigation.
        save_failed_output(
            input_data=input_data,
            raw_output=repaired_output,
            error=(
                f"First attempt: {first_error_text}; "
                f"Repair attempt: {str(second_error)}"
            ),
            prompt_version=PROMPT_VERSION,
        )

        # Never return raw model text.
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
    """
    POST /triage

    Accepts a support message and returns validated triage JSON.
    """

    # Step 1: Parse the incoming JSON.
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

    # Step 2: Make sure the body is a JSON object.
    if not isinstance(body, dict):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid request",
                "field": "body",
                "message": "Request body must be a JSON object",
            },
        )

    # Step 3: Validate input before any model call.
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

    # Step 4: Run stub mode or real model processing.
    return await run_triage(data)
