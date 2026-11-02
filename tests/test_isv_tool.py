"""ISV tool. Golden cases are the hand-worked examples in pricewise-pt's tests/test_isv.py."""

from datetime import date

import pytest
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import ValidationError

from pricewise_mcp.schemas import DISCLAIMER, VehicleInput
from pricewise_mcp.tax_tools import isv_result

ON = date(2026, 10, 1)


def car(first, fuel="petrol", **kw):
    return VehicleInput(first_registration=first, fuel=fuel, **kw)


def test_petrol_wltp():
    # (564.13 + 39.58) × 0.35 = 211.2985 -> 211.30, 65% age reduction
    r = isv_result(car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125, co2_standard="wltp"), ON)
    assert (r.total_eur, r.age_reduction) == (211.30, 0.65)
    assert (r.engine_component_eur, r.co2_component_eur) == (197.45, 13.85)
    assert r.regime == "normal" and not r.minimum_applied
    assert r.co2_standard_used == "wltp" and not r.co2_standard_assumed
    assert r.flags == [] and r.alternative_total_eur is None
    assert r.tax_year == 2026 and r.declaration_date == ON


def test_every_response_carries_sources_and_the_disclaimer():
    r = isv_result(car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125, co2_standard="wltp"), ON)
    assert r.disclaimer == DISCLAIMER and "not tax advice" in r.disclaimer
    assert any("Código do Imposto sobre Veículos" in s for s in r.sources)


def test_diesel_particles_exact_and_unknown():
    base = dict(fuel="diesel", engine_cc=1598, co2_g_km=115, co2_standard="wltp")
    clean = isv_result(car(date(2020, 3, 1), particles_g_km=0.0005, **base), ON)
    dirty = isv_result(car(date(2020, 3, 1), particles_g_km=0.002, **base), ON)
    unknown = isv_result(car(date(2020, 3, 1), **base), ON)
    assert clean.total_eur == 1217.64 and clean.particle_surcharge_eur == 0
    assert dirty.total_eur == 1217.64 + 500 and dirty.particle_surcharge_eur == 500
    assert unknown.total_eur == 1717.64
    assert any("V.5" in f for f in unknown.flags)


def test_the_minimum_applies_and_is_flagged():
    r = isv_result(car(date(2012, 1, 10), engine_cc=998, co2_g_km=95, co2_standard="nedc"), ON)
    assert r.total_eur == 100.0 and r.minimum_applied
    assert any("minimum" in f for f in r.flags)


def test_electric_pays_nothing_and_needs_no_engine_data():
    r = isv_result(car(date(2021, 1, 1), "electric"), ON)
    assert r.total_eur == 0.0 and r.regime == "electric" and r.flags == []


def test_unknown_standard_is_flagged_with_the_alternative_total():
    first = date(2018, 9, 1)
    explicit = {
        s: isv_result(car(first, engine_cc=1199, co2_g_km=125, co2_standard=s), ON).total_eur
        for s in ("nedc", "wltp")
    }
    r = isv_result(car(first, engine_cc=1199, co2_g_km=125), ON)
    assert r.total_eur == max(explicit.values())
    assert r.alternative_total_eur == min(explicit.values())
    assert r.co2_standard_assumed
    assert any("NEDC/WLTP" in f for f in r.flags)


@pytest.mark.parametrize(
    ("euro", "co2", "expected"),
    [("6d", 60, "normal"), ("6e-bis", 60, "plugin_hybrid")],
)
def test_plugin_hybrid_regime(euro, co2, expected):
    v = car(
        date(2024, 3, 1),
        "plugin_hybrid",
        engine_cc=1498,
        co2_g_km=co2,
        co2_standard="wltp",
        euro_norm=euro,
        electric_range_km=60,
    )
    assert isv_result(v, ON).regime == expected


def test_same_input_same_output():
    v = car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125, co2_standard="wltp")
    assert isv_result(v, ON) == isv_result(v, ON)


@pytest.mark.parametrize(
    "kw",
    [
        {"co2_g_km": 125},  # missing engine_cc
        {"engine_cc": 1199},  # missing co2_g_km
        {"engine_cc": 5, "co2_g_km": 125},  # engine too small
        {"engine_cc": 1199, "co2_g_km": -1},
        {"engine_cc": 1199, "co2_g_km": 125, "co2_standard": "epa"},
        {"engine_cc": 1199, "co2_g_km": 125, "turbo": True},  # unknown field
    ],
)
def test_invalid_vehicles_are_rejected(kw):
    with pytest.raises(ValidationError):
        car(date(2019, 6, 15), **kw)


def test_missing_fields_are_named_in_the_error():
    with pytest.raises(
        ValidationError,
        match=r"missing engine_cc \(field P\.1\) and co2_g_km \(field V\.7\).*petrol",
    ):
        car(date(2019, 6, 15))


def test_declaration_before_registration_is_a_tool_error():
    v = car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125, co2_standard="wltp")
    with pytest.raises(ToolError, match="before first_registration"):
        isv_result(v, date(2019, 1, 1))


def test_unavailable_tax_year_lists_the_available_ones():
    v = car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125, co2_standard="wltp")
    with pytest.raises(ToolError, match=r"No ISV tables for 2019.*2026"):
        isv_result(v, ON, tax_year=2019)
