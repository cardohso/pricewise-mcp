"""Resources: the versioned tax tables with their legal sources, and the
limitations document. Everything is read from the installed package."""

from __future__ import annotations

import json

from mcp.server.mcpserver import MCPServer
from pricewise.tax import tables

from pricewise_mcp.tax_tools import available_years

TAXES = ("isv", "iuc")

LIMITATIONS = """\
# Limitations of pricewise-mcp

## Tax tools (calculate_isv, calculate_iuc)
- **Not tax advice.** Results illustrate the 2026 tables of the Código do ISV and the Código do
  IUC. Confirm with the Autoridade Tributária e Aduaneira before relying on them.
- Scope: used passenger cars brought in from another EU/EEA state. Not covered: vehicles from
  outside the EU/EEA, commercial vehicles, motorcycles, and exemptions or special regimes beyond
  the hybrid regimes in the tables.
- IUC covers category B only (first registered on or after 2007-07-01). Older cars are rejected.
- IUC is one year at the table year's rates. Rates change; do not extrapolate past the table year.
- If the CO2 test standard (NEDC/WLTP) is unknown it is assumed from the registration date and
  the result says so. ISV then also reports the total under the other standard where both apply.
- If a diesel's particle value is missing, the surcharge is assumed due and the result says so.
- The declaration date is always an input, never "today", so results are reproducible.

## Valuation tool (estimate_price_range)
- Trained on **synthetic**, made-up listings (5 categories). Prices and ranges say nothing about
  any real market or car.
- The 50% and 80% ranges are calibrated on that synthetic data only; their coverage on real
  listings is unknown.
- Inputs outside the synthetic training range are flagged as extrapolation.

## Server
- No network calls and no file writes. Outputs are deterministic.
"""


def register(mcp: MCPServer) -> None:
    @mcp.resource(
        "pricewise://limitations",
        name="limitations",
        title="Limitations",
        description="What this server does not do: not tax advice, synthetic valuation data.",
        mime_type="text/markdown",
    )
    def limitations() -> str:
        return LIMITATIONS

    index = [
        {
            "tax": tax,
            "year": year,
            "uri": f"pricewise://tables/{tax}/{year}",
            "sources": tables.load(tax, year)["sources"],
        }
        for tax in TAXES
        for year in available_years(tax)
    ]

    @mcp.resource(
        "pricewise://tables",
        name="tables_index",
        title="Tax tables index",
        description="Which ISV and IUC table years are available, with their legal sources.",
        mime_type="application/json",
    )
    def tables_index() -> str:
        return json.dumps(index, ensure_ascii=False, indent=2)

    for entry in index:
        _register_table(mcp, entry["tax"], entry["year"])


def _register_table(mcp: MCPServer, tax: str, year: int) -> None:
    @mcp.resource(
        f"pricewise://tables/{tax}/{year}",
        name=f"{tax}_{year}",
        title=f"{tax.upper()} {year} tables",
        description=f"The {tax.upper()} {year} rate tables exactly as the calculator uses them, "
        "with the legal articles they come from in `sources`.",
        mime_type="application/json",
    )
    def table() -> str:
        return json.dumps(tables.load(tax, year), ensure_ascii=False, indent=2)
