"""Thin wrapper around the Anthropic SDK shared by every agent.

The core pattern used throughout this app: give Claude one "tool" that
represents "here is my final structured answer" and let it call that tool
when (and only when) it's ready. Until then it just replies with plain text
(e.g. the next interview question, or a request for clarification). This is
far more reliable than asking the model to emit raw JSON in prose.
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import anthropic

from app.config import settings

_client: Optional[anthropic.Anthropic] = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_configured:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Add it to your .env file "
                "(see .env.example) and restart the server."
            )
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


class ToolCallResult:
    """Result of a call_with_tool invocation."""

    def __init__(self, tool_input: Optional[Dict[str, Any]], text: str, raw_response: Any):
        self.tool_input = tool_input   # populated if the model called the tool
        self.text = text               # populated if the model replied with plain text instead
        self.raw_response = raw_response

    @property
    def called_tool(self) -> bool:
        return self.tool_input is not None


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
    """Call Claude with a single tool available. Returns either the tool's
    input (if Claude called it) or Claude's plain text reply."""
    client = get_client()
    tool = {
        "name": tool_name,
        "description": tool_description,
        "input_schema": tool_schema,
    }
    kwargs: Dict[str, Any] = dict(
        model=model or settings.model_quality,
        max_tokens=max_tokens,
        system=system,
        messages=messages,
        tools=[tool],
    )
    if force_tool:
        kwargs["tool_choice"] = {"type": "tool", "name": tool_name}

    try:
        response = client.messages.create(**kwargs)
    except anthropic.AuthenticationError:
        raise RuntimeError(
            "Anthropic rejected your API key (401). Check ANTHROPIC_API_KEY in your .env file — "
            "it needs to be a real key from https://console.anthropic.com/, not the placeholder."
        )
    except anthropic.APIConnectionError as exc:
        raise RuntimeError(f"Couldn't reach the Anthropic API — check your internet connection. ({exc})")
    except anthropic.APIStatusError as exc:
        raise RuntimeError(f"Anthropic API error ({exc.status_code}): {exc.message}")

    tool_input = None
    text_parts = []
    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            tool_input = block.input
        elif block.type == "text":
            text_parts.append(block.text)

    return ToolCallResult(tool_input=tool_input, text="\n".join(text_parts), raw_response=response)


def simple_completion(*, system: str, prompt: str, model: Optional[str] = None, max_tokens: int = 2048) -> str:
    """Plain text-in, text-out completion, no tools."""
    client = get_client()
    response = client.messages.create(
        model=model or settings.model_quality,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(block.text for block in response.content if block.type == "text")
