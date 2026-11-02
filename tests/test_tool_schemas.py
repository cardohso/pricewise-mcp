"""What a client sees when it lists the tools."""

import anyio
import pytest
from mcp.client import Client

from pricewise_mcp.server import mcp


@pytest.fixture(scope="module")
def tools():
    async def run():
        async with Client(mcp) as client:
            return (await client.list_tools()).tools

    return {t.name: t for t in anyio.run(run)}


def test_tax_tools_are_listed(tools):
    assert {"calculate_isv", "calculate_iuc"} <= set(tools)


def test_tools_are_marked_read_only_and_closed_world(tools):
    for t in tools.values():
        a = t.annotations
        assert a.read_only_hint and a.idempotent_hint and not a.open_world_hint, t.name


def test_descriptions_tell_the_client_to_relay_flags_and_the_disclaimer(tools):
    for name in ("calculate_isv", "calculate_iuc"):
        d = tools[name].description
        assert "`flags`" in d and "`disclaimer`" in d and "not tax advice" in d, name


def test_declaration_date_is_required_for_isv(tools):
    assert set(tools["calculate_isv"].input_schema["required"]) == {
        "vehicle",
        "declaration_date",
    }
    assert tools["calculate_iuc"].input_schema["required"] == ["vehicle"]


def _described(schema):
    """Every property in the input schema (including $defs) has a description."""
    props = [schema["properties"], *(d["properties"] for d in schema.get("$defs", {}).values())]
    return {k: "description" in v for p in props for k, v in p.items()}


@pytest.mark.parametrize("name", ["calculate_isv", "calculate_iuc"])
def test_every_input_field_has_a_description(tools, name):
    missing = [k for k, ok in _described(tools[name].input_schema).items() if not ok]
    assert missing == []


@pytest.mark.parametrize("name", ["calculate_isv", "calculate_iuc"])
def test_outputs_are_structured(tools, name):
    out = tools[name].output_schema
    assert {"total_eur", "flags", "sources", "disclaimer"} <= set(out["properties"])
