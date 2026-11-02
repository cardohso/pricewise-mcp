"""What an LLM client reads when it gets the arguments wrong: one line per problem,
the field, what was sent, and a hint for common mistakes. No pydantic internals."""

import pytest
from helpers import with_client

VEHICLE = {
    "first_registration": "2019-06-15",
    "fuel": "petrol",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp",
}


def error_text(name, args):
    r = with_client(lambda c: c.call_tool(name, args))
    assert r.is_error
    return r.content[0].text


def isv_error(**vehicle_changes):
    vehicle = {**VEHICLE, **vehicle_changes}
    return error_text("calculate_isv", {"vehicle": vehicle, "declaration_date": "2026-10-01"})


@pytest.mark.parametrize(
    ("changes", "expected"),
    [
        ({"fuel": "gasoline"}, "Hint: use 'petrol' for 'gasoline'"),
        ({"fuel": "PHEV"}, "Hint: use 'plugin_hybrid' for 'PHEV'"),
        ({"first_registration": "15/06/2019"}, "send '2019-06-15'"),
        ({"first_registration": "June 2019"}, "YYYY-MM-DD"),
        ({"engine_cc": 1.2}, "1.2 L is about 1200 cm3"),
        ({"engine_cc": 2}, "2 L is about 2000 cm3"),
        ({"cc": 1199}, "did you mean 'engine_cc'?"),
        ({"co2": 125}, "did you mean 'co2_g_km'?"),
        ({"engine_cc": None}, "missing engine_cc (field P.1)"),
    ],
)
def test_common_mistakes_get_a_hint(changes, expected):
    assert expected in isv_error(**changes)


def test_missing_argument_is_named():
    text = error_text("calculate_isv", {"vehicle": VEHICLE})
    assert text.splitlines() == [
        "Invalid arguments for calculate_isv. Fix these and call again:",
        "- declaration_date: required",
    ]


def test_every_problem_is_reported_at_once():
    text = isv_error(fuel="gasoline", engine_cc=1.2, first_registration="15/06/2019")
    assert len(text.splitlines()) == 4  # header + three problems


def test_no_pydantic_internals_reach_the_client():
    text = isv_error(fuel="gasoline", cc=1, first_registration="x")
    for leak in ("pydantic.dev", "Arguments", "type=", "input_type", "validation error for"):
        assert leak not in text


def test_valuation_synonyms():
    args = {"category": "SUV", "age_years": 6, "usage": 90_000}
    assert "use 'crossover' for 'SUV'" in error_text("estimate_price_range", args)
    args = {"category": "compact", "age_years": 6, "mileage": 90_000}
    text = error_text("estimate_price_range", args)
    assert "did you mean 'usage'?" in text and "usage: required" in text


def test_unknown_top_level_argument_is_an_error_even_if_the_rest_is_valid():
    args = {"vehicle": VEHICLE, "declaration_date": "2026-10-01", "taxyear": 2026}
    text = error_text("calculate_isv", args)
    assert "- taxyear: extra inputs are not permitted" in text
    assert "did you mean 'tax_year'?" in text


def test_category_a_says_not_to_retry():
    vehicle = {**VEHICLE, "first_registration": "2005-01-01"}
    text = error_text("calculate_iuc", {"vehicle": vehicle})
    assert "category B only" in text and "do not retry" in text


def test_declaration_outside_the_table_year_is_flagged():
    r = with_client(
        lambda c: c.call_tool(
            "calculate_isv", {"vehicle": VEHICLE, "declaration_date": "2027-02-01"}
        )
    )
    assert any("2026 tables were used" in f for f in r.structured_content["flags"])


def test_descriptions_are_clean_text():
    tools = with_client(lambda c: c.list_tools()).tools
    for t in tools:
        assert "\n        " not in t.description, t.name  # no docstring indentation
        assert len(t.description) < 1200, t.name
