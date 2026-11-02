"""Price-range tool. The model is trained on pricewise-pt's synthetic market, so
every answer says so. It is fitted once, in a background thread started at
server launch; a call that arrives before it finishes waits for it."""

from __future__ import annotations

import threading
from datetime import date
from typing import Annotated, Literal

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations
from pricewise.synthetic import CATEGORIES, generate
from pricewise.valuation import Item, Valuer
from pydantic import BaseModel, Field

Category = Literal["compact", "hatchback", "crossover", "estate", "electric"]
assert set(CATEGORIES) == set(Category.__args__)  # keep the schema in step with the library

SYNTHETIC_NOTICE = (
    "Trained on synthetic, made-up listings. Prices and ranges say nothing about any real "
    "market; they show how the method behaves."
)
READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)
_QUERY_DATE = date(2025, 1, 1)  # required by Item, unused by the model


class PriceRange(BaseModel):
    low_eur: float
    high_eur: float


class PriceEstimate(BaseModel):
    point_eur: float = Field(description="Best single estimate, in euros.")
    range_50: PriceRange = Field(description="Half of similar items land inside this range.")
    range_80: PriceRange = Field(description="Eight in ten similar items land inside this range.")
    comparables_median_eur: float | None = Field(
        description="Median price of similar items in the synthetic pool (same category, age "
        "within a year, usage within 20%); null if fewer than 3 are similar."
    )
    data_source: Literal["synthetic"] = "synthetic"
    flags: list[str] = Field(description="Caveats to relay, including extrapolation warnings.")
    notice: str = SYNTHETIC_NOTICE


class ValuationService:
    def __init__(self, n: int = 4_000) -> None:
        self._n = n
        self._lock = threading.Lock()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None

    def warm(self) -> None:
        """Start fitting in the background (idempotent)."""
        with self._lock:
            if self._thread is None:
                self._thread = threading.Thread(target=self._fit, daemon=True)
                self._thread.start()

    def _fit(self) -> None:
        pool = generate(self._n)
        self._valuer = Valuer().fit(pool)
        self._bounds = {
            "age_years": (min(i.age_years for i in pool), max(i.age_years for i in pool)),
            "usage": (min(i.usage for i in pool), max(i.usage for i in pool)),
        }
        self._ready.set()

    def estimate(
        self, category: str, age_years: float, usage: float, condition: str | None
    ) -> PriceEstimate:
        self.warm()
        self._ready.wait()
        item = Item("query", "query", category, age_years, usage, _QUERY_DATE, 0.0, condition)
        e = self._valuer.estimate(item)
        flags = []
        for name, value in (("age_years", age_years), ("usage", usage)):
            lo, hi = self._bounds[name]
            if not lo <= value <= hi:
                flags.append(
                    f"{name}={value:g} is outside the synthetic training range "
                    f"({lo:g} to {hi:g}); the estimate is an extrapolation"
                )
        return PriceEstimate(
            point_eur=round(e.point, 2),
            range_50=PriceRange(low_eur=round(e.likely[0], 2), high_eur=round(e.likely[1], 2)),
            range_80=PriceRange(low_eur=round(e.wide[0], 2), high_eur=round(e.wide[1], 2)),
            comparables_median_eur=e.comparables,
            flags=flags,
        )


service = ValuationService()


DESCRIPTION = """\
Demo of calibrated price ranges: estimate a used car's asking price from its body category, \
age and kilometres, with a range half of similar cars fall in (range_50) and one eight in ten \
fall in (range_80).

The model is trained on SYNTHETIC, made-up listings. Never present the result as the value of \
a real car or use it for a purchase or sale decision: say it comes from a synthetic demo \
market, and relay `flags`.

The first call after the server starts can take up to about 20 seconds while the model is \
fitted."""


def register(mcp: MCPServer) -> None:
    @mcp.tool(
        name="estimate_price_range",
        title="Estimate price range (synthetic demo)",
        description=DESCRIPTION,
        annotations=READ_ONLY,
    )
    def estimate_price_range(
        category: Annotated[
            Category,
            Field(
                description="Body category. Pick the closest: an SUV is 'crossover', a "
                "small city car is 'hatchback', a station wagon ('carrinha') is 'estate', "
                "any battery-electric car is 'electric'."
            ),
        ],
        age_years: Annotated[float, Field(ge=0, le=40, description="Age of the item in years.")],
        usage: Annotated[
            float,
            Field(ge=0, le=2_000_000, description="Odometer reading in km (not miles)."),
        ],
        condition: Annotated[
            Literal["good", "fair", "poor"] | None,
            Field(description="Condition, if known. Omit when unknown (many listings omit it)."),
        ] = None,
    ) -> PriceEstimate:
        return service.estimate(category, age_years, usage, condition)
