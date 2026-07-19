"""Thin wrapper around the Groq SDK shared by every agent.

Groq is fully free (no credit card), runs Llama 3.3 70B, and is
OpenAI-API-compatible. The core pattern: give the model one "tool"
representing its final structured answer and let it call that tool when
ready. Until then it replies with plain text (e.g. next interview question).

Key format difference from Anthropic:
  - Anthropic tools use "input_schema", response uses block.input (dict)
  - Groq/OpenAI tools use "parameters", response uses tc.function.arguments (JSON string)
Everything else (JSON Schema content, message roles) is identical.
"""
from __future__ import annotations

import json
import time
from typing import Any, Dict, List, Optional

from groq import Groq, RateLimitError, AuthenticationError, APIConnectionError, APIStatusError

from app.config import settings

_client: Optional[Groq] = None


def get_client() -> Groq:
    global _client
    if _client is None:
        if not settings.groq_configured:
            raise RuntimeError(
                "GROQ_API_KEY is not set. "
                "Sign up free at https://console.groq.com/ (no credit card required), "
                "create an API key, add it to your .env file as GROQ_API_KEY=..., "
                "then restart the server."
            )
        _client = Groq(api_key=settings.groq_api_key)
    return _client


class ToolCallResult:
    def __init__(self, tool_input: Optional[Dict[str, Any]], text: str, raw_response: Any):
        self.tool_input = tool_input
        self.text = text
        self.raw_response = raw_response

    @property
    def called_tool(self) -> bool:
        return self.tool_input is not None


def _make_groq_tool(tool_name: str, tool_description: str, tool_schema: Dict[str, Any]) -> Dict[str, Any]:
    """Convert from our internal format to Groq/OpenAI function calling format."""
    return {
        "type": "function",
        "function": {
            "name": tool_name,
            "description": tool_description,
            "parameters": tool_schema,   # same JSON Schema, just "parameters" not "input_schema"
        },
    }


def _call_with_retry(client: Groq, max_retries: int = 3, **kwargs) -> Any:
    """Call the Groq API with automatic exponential backoff on rate limit errors."""
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(**kwargs)
        except RateLimitError:
            if attempt == max_retries - 1:
                raise RuntimeError(
                    "Groq rate limit reached. You are on the free tier which allows "
                    "~1,000 requests/day. Wait a minute and try again, or space out "
                    "your apply pipeline runs."
                )
            wait = 2 ** attempt   # 1s, 2s, 4s
            time.sleep(wait)
    raise RuntimeError("Max retries exceeded.")


def call_with_tool(
    *,
    system: str,
    messages: List[Dict[str, Any]],
    tool_name: str,
    tool_description: str,
    tool_schema: Dict[str, Any],
    model: Optional[str] = None,
    max_tokens: int = 4096,
    force_tool: bool = False,
) -> ToolCallResult:
    client = get_client()
    groq_messages = [{"role": "system", "content": system}] + [
        {"role": m["role"], "content": m["content"]} for m in messages
    ]
    tool = _make_groq_tool(tool_name, tool_description, tool_schema)

    kwargs: Dict[str, Any] = dict(
        model=model or settings.model_quality,
        max_tokens=max_tokens,
        messages=groq_messages,
        tools=[tool],
    )
    if force_tool:
        kwargs["tool_choice"] = {"type": "function", "function": {"name": tool_name}}

    try:
        response = _call_with_retry(client, **kwargs)
    except AuthenticationError:
        raise RuntimeError(
            "Groq rejected your API key (401). Check GROQ_API_KEY in your .env — "
            "get a free key at https://console.groq.com/ (no card needed)."
        )
    except APIConnectionError as exc:
        raise RuntimeError(f"Couldn't reach Groq — check your internet connection. ({exc})")
    except APIStatusError as exc:
        raise RuntimeError(f"Groq API error ({exc.status_code}): {exc.message}")

    message = response.choices[0].message
    tool_input = None
    text = message.content or ""

    if message.tool_calls:
        for tc in message.tool_calls:
            if tc.function.name == tool_name:
                try:
                    tool_input = json.loads(tc.function.arguments)
                except json.JSONDecodeError as exc:
                    raise RuntimeError(
                        f"Model returned malformed JSON in tool call: {exc}\n"
                        f"Raw: {tc.function.arguments[:300]}"
                    )
                break

    return ToolCallResult(tool_input=tool_input, text=text, raw_response=response)


def simple_completion(
    *, system: str, prompt: str, model: Optional[str] = None, max_tokens: int = 2048
) -> str:
    client = get_client()
    try:
        response = _call_with_retry(
            client,
            model=model or settings.model_quality,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
        )
    except AuthenticationError:
        raise RuntimeError("Groq rejected your API key. Check GROQ_API_KEY in .env.")
    except APIConnectionError as exc:
        raise RuntimeError(f"Couldn't reach Groq: {exc}")
    return response.choices[0].message.content or ""
