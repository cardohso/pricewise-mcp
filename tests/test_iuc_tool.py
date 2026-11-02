"""IUC tool. Golden cases are the hand-worked examples in pricewise-pt's tests/test_iuc.py."""

from datetime import date

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from pricewise_mcp.schemas import DISCLAIMER, VehicleInput
from pricewise_mcp.tax_tools import iuc_result


def car(first, fuel="petrol", **kw):
    return VehicleInput(first_registration=first, fuel=fuel, **kw)


def test_petrol(no_file_writes):
    # (31.77 + 65.15) × 1.15 = 111.458 -> 111.46
    r = iuc_result(car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125, co2_standard="wltp"))
    assert r.total_eur == 111.46 and r.year_coefficient == 1.15
    assert (r.engine_component_eur, r.co2_component_eur) == (31.77, 65.15)
    assert r.flags == [] and not r.co2_standard_assumed
    assert r.disclaimer == DISCLAIMER and r.sources


def test_diesel_extra_is_outside_the_coefficient():
    r = iuc_result(
        car(date(2020, 3, 1), "diesel", engine_cc=1598, co2_g_km=115, co2_standard="wltp")
    )
    assert (r.total_eur, r.diesel_extra_eur) == (158.29, 10.07)


def test_high_co2_extra():
    r = iuc_result(car(date(2018, 2, 1), engine_cc=1998, co2_g_km=230, co2_standard="wltp"))
    assert (r.total_eur, r.co2_extra_eur) == (426.83, 31.77)


def test_electric_pays_nothing():
    assert iuc_result(car(date(2022, 1, 1), "electric")).total_eur == 0.0


def test_unknown_standard_is_assumed_and_flagged():
    r = iuc_result(car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125))
    assert r.total_eur == 111.46  # 2019 is assumed WLTP
    assert r.co2_standard_assumed and r.co2_standard_used == "wltp"
    assert any("WLTP" in f and "certificate of conformity" in f for f in r.flags)


def test_category_a_is_a_tool_error_that_says_why():
    v = car(date(2006, 12, 1), engine_cc=1400, co2_g_km=150)
    with pytest.raises(ToolError, match=r"category A.*2007-07-01"):
        iuc_result(v)


def test_unavailable_tax_year_lists_the_available_ones():
    v = car(date(2019, 6, 15), engine_cc=1199, co2_g_km=125, co2_standard="wltp")
    with pytest.raises(ToolError, match=r"No IUC tables for 2030.*2026"):
        iuc_result(v, tax_year=2030)
