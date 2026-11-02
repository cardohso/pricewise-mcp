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


def register(mcp: MCPServer) -> None:
    @mcp.tool(name="estimate_price_range", title="Estimate price range", annotations=READ_ONLY)
    def estimate_price_range(
        category: Annotated[Category, Field(description="Item category in the synthetic market.")],
        age_years: Annotated[float, Field(ge=0, le=40, description="Age of the item in years.")],
        usage: Annotated[
            float,
            Field(ge=0, le=2_000_000, description="Distance driven, in km."),
        ],
        condition: Annotated[
            Literal["good", "fair", "poor"] | None,
            Field(description="Condition, if known. Omit when unknown (many listings omit it)."),
        ] = None,
    ) -> PriceEstimate:
        """Estimate an asking price with calibrated 50% and 80% ranges.

        The model is trained on SYNTHETIC data, not a real market: treat the numbers as a demo
        of calibrated uncertainty, never as a valuation of a real car. Always tell the user
        this, and relay `flags`. The first call after server start may wait a few seconds
        while the model finishes fitting."""
        return service.estimate(category, age_years, usage, condition)
