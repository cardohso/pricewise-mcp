import json

from helpers import with_client
from mcp.shared.exceptions import MCPError
from pricewise.tax import tables


def read(uri):
    r = with_client(lambda c: c.read_resource(uri))
    return r.contents[0].text


def test_resources_are_listed():
    uris = {r.uri for r in with_client(lambda c: c.list_resources()).resources}
    assert uris == {
        "pricewise://limitations",
        "pricewise://tables",
        "pricewise://tables/isv/2026",
        "pricewise://tables/iuc/2026",
    }


def test_tables_are_served_exactly_as_the_library_loads_them():
    for tax in ("isv", "iuc"):
        served = json.loads(read(f"pricewise://tables/{tax}/2026"))
        assert served == tables.load(tax, 2026)
        assert any("Diário da República" in s for s in served["sources"])


def test_index_lists_every_table_with_sources():
    index = json.loads(read("pricewise://tables"))
    assert [(e["tax"], e["year"]) for e in index] == [("isv", 2026), ("iuc", 2026)]
    assert all(e["sources"] for e in index)


def test_limitations_cover_tax_advice_and_synthetic_data():
    text = read("pricewise://limitations")
    assert "Not tax advice" in text and "synthetic" in text.lower()
    assert "category A" in text or "category B" in text


def test_unknown_resource_is_an_error_that_names_the_uri():
    async def attempt(client):
        try:
            await client.read_resource("pricewise://tables/isv/1999")
        except MCPError as e:
            return e
        return None

    error = with_client(attempt)
    assert error is not None and "pricewise://tables/isv/1999" in str(error)


def test_explain_prompt_names_the_tools_and_forbids_guessing():
    args = {"vehicle_description": "2019 Golf 1.0 petrol", "declaration_date": "2026-10-01"}
    p = with_client(lambda c: c.get_prompt("explain_tax_breakdown", args))
    text = p.messages[0].content.text
    assert "calculate_isv" in text and "calculate_iuc" in text
    assert "2019 Golf 1.0 petrol" in text and "Do not guess" in text and "not tax advice" in text
