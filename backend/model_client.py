"""One shared, bounded structured-output path for supplier and product analysis."""
import json
import math

from openai import OpenAI
from pydantic import ValidationError

from backend.config import (OPENAI_API_KEY, OPENAI_MODEL, OPENAI_MAX_OUTPUT_TOKENS,
                            OPENAI_INPUT_USD_PER_MILLION, OPENAI_OUTPUT_USD_PER_MILLION)
from backend.research_context import JobStopped, LimitReached

client = OpenAI(api_key=OPENAI_API_KEY or "unconfigured", max_retries=0)


def request_structured(messages, response_model, context, *, schema_name):
    schema = response_model.model_json_schema()
    if not OPENAI_API_KEY:
        return {"error": "openai_not_configured"}
    if not all(math.isfinite(rate) and rate > 0 for rate in [OPENAI_INPUT_USD_PER_MILLION, OPENAI_OUTPUT_USD_PER_MILLION]):
        return {"error": "configure_model_pricing_for_budget_guard"}
    input_bound = sum(len(m["content"].encode()) for m in messages) + len(json.dumps(schema).encode()) + 512
    maximum = (input_bound * OPENAI_INPUT_USD_PER_MILLION + OPENAI_MAX_OUTPUT_TOKENS * OPENAI_OUTPUT_USD_PER_MILLION) / 1_000_000
    operation = context.reserve("openai", maximum, model=OPENAI_MODEL, purpose=schema_name)
    try:
        response = client.chat.completions.create(
            model=OPENAI_MODEL, messages=messages,
            response_format={"type": "json_schema", "json_schema": {"name": schema_name, "strict": True, "schema": schema}},
            extra_body={"max_completion_tokens": OPENAI_MAX_OUTPUT_TOKENS, "store": False, "service_tier": "default"},
            timeout=max(1, min(40, context.remaining_seconds())),
        )
        usage = response.usage
        if usage:
            cost = (usage.prompt_tokens * OPENAI_INPUT_USD_PER_MILLION + usage.completion_tokens * OPENAI_OUTPUT_USD_PER_MILLION) / 1_000_000
            context.settle_model(operation, cost)
            context.record(operation, input_tokens=usage.prompt_tokens, output_tokens=usage.completion_tokens)
        context.record(operation, response_id=response.id)
        context.checkpoint()
        if response.choices[0].finish_reason != "stop":
            return {"error": "model_response_incomplete"}
        return response_model.model_validate_json(response.choices[0].message.content).model_dump()
    except (JobStopped, LimitReached):
        raise
    except (ValidationError, ValueError, TypeError):
        context.record(operation, status="invalid_response")
        return {"error": "invalid_model_output"}
    except Exception as exc:
        context.record(operation, status="error", error_type=type(exc).__name__)
        return {"error": "model_request_failed:" + type(exc).__name__}
