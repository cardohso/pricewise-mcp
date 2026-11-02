import pytest
from helpers import with_client

from pricewise_mcp.valuation_tools import ValuationService

ARGS = {"category": "compact", "age_years": 6, "usage": 90_000, "condition": "good"}


def estimate(**overrides):
    r = with_client(lambda c: c.call_tool("estimate_price_range", {**ARGS, **overrides}))
    return r


def test_estimate_has_nested_calibrated_ranges_and_says_it_is_synthetic(no_file_writes):
    r = estimate()
    assert not r.is_error
    e = r.structured_content
    assert e["data_source"] == "synthetic" and "synthetic" in e["notice"]
    lo50, hi50 = e["range_50"]["low_eur"], e["range_50"]["high_eur"]
    lo80, hi80 = e["range_80"]["low_eur"], e["range_80"]["high_eur"]
    assert lo80 < lo50 < e["point_eur"] < hi50 < hi80
    assert e["flags"] == []


def test_estimate_matches_the_library_example_and_is_deterministic():
    # pricewise-pt@b880ec2 examples/estimate.py prints these for the same item.
    first, second = estimate().structured_content, estimate().structured_content
    assert first == second
    assert first["point_eur"] == pytest.approx(10504.17, abs=0.01)
    assert first["range_50"]["low_eur"] == pytest.approx(9362.40, abs=0.01)
    assert first["range_80"]["high_eur"] == pytest.approx(12704.31, abs=0.01)
    assert first["comparables_median_eur"] == 10190.0


def test_condition_is_optional():
    assert not estimate(condition=None).is_error


def test_outside_the_training_range_is_flagged():
    flags = estimate(age_years=30).structured_content["flags"]
    assert len(flags) == 1 and "extrapolation" in flags[0] and "age_years" in flags[0]


@pytest.mark.parametrize(
    "overrides",
    [
        {"category": "truck"},
        {"age_years": -1},
        {"usage": 3_000_000},
        {"condition": "mint"},
    ],
)
def test_invalid_inputs_are_rejected(overrides):
    assert estimate(**overrides).is_error


def test_warm_starts_one_thread_only():
    s = ValuationService(n=50)
    s.warm()
    first = s._thread
    s.warm()
    assert s._thread is first
