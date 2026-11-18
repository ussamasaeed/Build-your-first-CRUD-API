
import json

from app.llm.schema import TriageOutput


def extract_json_object(raw_text: str) -> dict:
    """
    Find the first valid JSON object in model output.
    Handles code fences and introductory text.
    """
    if not isinstance(raw_text, str):
        raise ValueError("Model output was not text")

    decoder = json.JSONDecoder()

    for index, character in enumerate(raw_text):
        if character == "{":
            try:
                result, _ = decoder.raw_decode(raw_text[index:])
                if not isinstance(result, dict):
                    continue
                return result
            except json.JSONDecodeError:
                continue

    raise ValueError("No valid JSON object found in model output")


def parse_and_validate(raw_text: str) -> TriageOutput:
    parsed = extract_json_object(raw_text)
    return TriageOutput.model_validate(parsed)
