"""Argument errors an LLM client can act on.

The SDK reports invalid arguments as pydantic's raw text: internal model names, an
echo of the whole input, error codes and a pydantic.dev URL. This middleware
validates ``tools/call`` arguments with the tool's own validator first and, on
failure, answers with one line per problem: the field, what is wrong, what was
sent, and a hint when the mistake is a common one (litres for cm3, "gasoline" for
"petrol", day/month/year dates)."""

from __future__ import annotations

import difflib
import re
from typing import Any

from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, ValidationError

from pricewise_mcp.schemas import VehicleInput

SYNONYMS = {
    "gasoline": "petrol",
    "gas": "petrol",
    "gasolina": "petrol",
    "benzine": "petrol",
    "gasoleo": "diesel",
    "gasóleo": "diesel",
    "ev": "electric",
    "bev": "electric",
    "eletrico": "electric",
    "elétrico": "electric",
    "phev": "plugin_hybrid",
    "plug-in hybrid": "plugin_hybrid",
    "plugin hybrid": "plugin_hybrid",
    "hev": "hybrid",
    "hibrido": "hybrid",
    "híbrido": "hybrid",
    "suv": "crossover",
    "wagon": "estate",
    "station wagon": "estate",
    "carrinha": "estate",
    "city car": "hatchback",
}
FIELD_ALIASES = {
    "cc": "engine_cc",
    "displacement": "engine_cc",
    "engine_size": "engine_cc",
    "cilindrada": "engine_cc",
    "co2": "co2_g_km",
    "emissions": "co2_g_km",
    "registration_date": "first_registration",
    "first_registration_date": "first_registration",
    "fuel_type": "fuel",
    "km": "usage",
    "mileage": "usage",
    "odometer": "usage",
    "age": "age_years",
}
_DMY = re.compile(r"^(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})$")
_NESTED = {"vehicle": VehicleInput}


def _path(loc: tuple) -> str:
    return ".".join(str(p) for p in loc) or "(arguments)"


def _shown(value: Any) -> str:
    text = repr(value)
    return text if len(text) <= 60 else text[:57] + "..."


def _hint(err: dict, arg_model: type[BaseModel] | None) -> str | None:
    loc, kind, value = err["loc"], err["type"], err.get("input")
    field = str(loc[-1]) if loc else ""
    if kind == "literal_error" and isinstance(value, str):
        better = SYNONYMS.get(value.strip().lower())
        if better:
            return f"use '{better}' for '{value}'"
    if kind.startswith("date") and isinstance(value, str):
        m = _DMY.match(value.strip())
        if m:
            d, mo, y = m.groups()
            return (
                f"dates are YYYY-MM-DD; if '{value}' is day/month/year, send "
                f"'{y}-{int(mo):02d}-{int(d):02d}'"
            )
        return "dates are ISO 8601, YYYY-MM-DD (e.g. 2019-06-15)"
    if field == "engine_cc" and isinstance(value, int | float) and value < 50:
        return (
            f"engine_cc is in cm3, not litres: {value} L is about {round(value * 1000)} cm3; "
            "use the exact value from field P.1 if known"
        )
    if kind == "extra_forbidden":
        parent = _NESTED.get(str(loc[0])) if len(loc) > 1 else arg_model
        allowed = list(parent.model_fields) if parent else []
        alias = FIELD_ALIASES.get(field.lower())
        close = [alias] if alias in allowed else difflib.get_close_matches(field, allowed, n=1)
        hint = f"allowed fields: {', '.join(allowed)}" if allowed else ""
        return (f"did you mean '{close[0]}'? " if close else "") + hint or None
    return None


def unknown_arguments(arguments: dict, arg_model: type[BaseModel] | None) -> list[dict]:
    """Top-level arguments the tool does not take. The SDK drops these silently, so a
    misnamed optional argument would fall back to its default without a word."""
    if arg_model is None:
        return []
    known = set(arg_model.model_fields)
    return [
        {
            "type": "extra_forbidden",
            "loc": (k,),
            "msg": "Extra inputs are not permitted",
            "input": v,
        }
        for k, v in arguments.items()
        if k not in known
    ]


def describe(tool: str, errors: list[dict], arg_model: type[BaseModel] | None = None) -> str:
    lines = [f"Invalid arguments for {tool}. Fix these and call again:"]
    for err in errors:
        msg = err["msg"].removeprefix("Value error, ")
        if err["type"] == "missing":
            line = f"- {_path(err['loc'])}: required"
        elif err["type"] == "value_error":
            line = f"- {_path(err['loc'])}: {msg}"
        else:
            line = (
                f"- {_path(err['loc'])}: {msg[:1].lower() + msg[1:]} (got {_shown(err['input'])})"
            )
        hint = _hint(err, arg_model)
        lines.append(line + (f". Hint: {hint}" if hint else ""))
    return "\n".join(lines)


class ReadableArgumentErrors:
    """Server middleware: replaces pydantic's raw argument errors with ``describe``."""

    def __init__(self) -> None:
        self.server = None  # set once the server exists

    def _tool(self, name: Any):
        # Uses the SDK's private tool registry (mcp 2.x). If it moves, this falls back
        # to the SDK's own message; tests/test_errors.py fails loudly in that case.
        manager = getattr(self.server, "_tool_manager", None)
        get = getattr(manager, "get_tool", None)
        return get(name) if get and isinstance(name, str) else None

    async def __call__(self, ctx, call_next):
        if ctx.method == "tools/call" and isinstance(ctx.params, dict):
            tool = self._tool(ctx.params.get("name"))
            meta = getattr(tool, "fn_metadata", None)
            if meta is not None:
                arguments = ctx.params.get("arguments") or {}
                arg_model = getattr(meta, "arg_model", None)
                errors = unknown_arguments(arguments, arg_model)
                try:
                    meta.validate_arguments(arguments)
                except ValidationError as exc:
                    errors += exc.errors(include_url=False)
                if errors:
                    text = describe(tool.name, errors, arg_model)
                    return CallToolResult(
                        content=[TextContent(type="text", text=text)], is_error=True
                    )
        return await call_next(ctx)
