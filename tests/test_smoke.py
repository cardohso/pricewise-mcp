import anyio
from mcp.client import Client

from pricewise_mcp.server import mcp

PETROL_2019 = {
    "first_registration": "2019-06-15",
    "fuel": "petrol",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp",
}


def call(name, args):
    async def run():
        async with Client(mcp) as client:
            return await client.call_tool(name, args)

    return anyio.run(run)


def test_isv_through_a_client_returns_structured_output():
    r = call("calculate_isv", {"vehicle": PETROL_2019, "declaration_date": "2026-10-01"})
    assert not r.is_error
    assert r.structured_content["total_eur"] == 211.30
    assert r.structured_content["declaration_date"] == "2026-10-01"


def test_a_domain_error_reaches_the_client_with_its_message():
    r = call("calculate_isv", {"vehicle": PETROL_2019, "declaration_date": "2019-01-01"})
    assert r.is_error and "before first_registration" in r.content[0].text


def test_a_validation_error_reaches_the_client_and_names_the_field():
    bad = {k: v for k, v in PETROL_2019.items() if k != "engine_cc"}
    r = call("calculate_iuc", {"vehicle": bad})
    assert r.is_error and "engine_cc required when fuel is 'petrol'" in r.content[0].text
