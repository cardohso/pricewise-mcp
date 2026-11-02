"""ISV and IUC tools: thin, typed wrappers over ``pricewise.tax``. All the tax
arithmetic stays in the library; this module validates, maps errors to
messages a caller can act on, and attaches sources and the disclaimer."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pricewise.tax import CategoryANotSupported, Fuel, Vehicle, isv, iuc
from pricewise.tax import tables as _tables
from pydantic import Field

from pricewise_mcp.schemas import IsvResult, IucResult, VehicleInput

READ_ONLY = ToolAnnotations(
    read_only_hint=True, destructive_hint=False, idempotent_hint=True, open_world_hint=False
)

TaxYear = Annotated[
    int,
    Field(
        description="Year of the tax tables to use. Only years listed in the "
        "pricewise://tables resource are available (currently 2026)."
    ),
]


ISV_DESCRIPTION = """\
Compute ISV (Imposto sobre Veículos), Portugal's one-off registration tax, due when a used \
passenger car from another EU/EEA state is registered in Portugal ("legalizar um carro \
importado").

Inputs come from the car's documents: first-registration date (field B), fuel, engine cc \
(P.1) and CO2 g/km (V.7), plus the declaration date. If the user does not know engine_cc or \
co2_g_km, ask them; do not estimate. If the CO2 test standard (NEDC/WLTP) or a diesel's \
particle value is unknown, call anyway: the result assumes the costlier case and says so in \
`flags`.

Returns total_eur, its components and the legal sources. Always relay `flags` and \
`disclaimer` to the user: this is an illustration, not tax advice."""

IUC_DESCRIPTION = """\
Compute one year of IUC (Imposto Único de Circulação, the "selo do carro"), Portugal's \
yearly circulation tax, for a passenger car first registered in the EU/EEA on or after \
1 July 2007 (category B).

Same vehicle object as calculate_isv. If the user does not know engine_cc or co2_g_km, ask \
them; do not estimate. An unknown CO2 standard is assumed from the registration year and \
flagged. Cars first registered before 1 July 2007 return an error: tell the user this server \
cannot compute them, and do not retry with a different date.

Returns total_eur for one year at the tax_year rates. Always relay `flags` and `disclaimer` \
to the user: this is an illustration, not tax advice."""


def available_years(tax: str) -> list[int]:
    return sorted(int(p.stem.rsplit("_", 1)[1]) for p in _tables.TABLES_DIR.glob(f"{tax}_*.json"))


def _tables_for(tax: str, year: int) -> dict:
    years = available_years(tax)
    if year not in years:
        raise ToolError(
            f"No {tax.upper()} tables for {year}. Available years: {', '.join(map(str, years))}."
        )
    return _tables.load(tax, year)


def to_vehicle(v: VehicleInput) -> Vehicle:
    return Vehicle(
        first_registration=v.first_registration,
        fuel=Fuel(v.fuel),
        cc=v.engine_cc,
        co2_g_km=v.co2_g_km,
        co2_standard=None if v.co2_standard == "unknown" else v.co2_standard,
        euro_norm=v.euro_norm,
        particles_g_km=v.particles_g_km,
        electric_range_km=v.electric_range_km,
        hybrid_base_fuel=Fuel(v.hybrid_base_fuel),
    )


def isv_result(
    vehicle: VehicleInput, declaration_date: date, tax_year: int = _tables.CURRENT_YEAR
) -> IsvResult:
    if declaration_date < vehicle.first_registration:
        raise ToolError(
            f"declaration_date {declaration_date} is before first_registration "
            f"{vehicle.first_registration}; the car cannot be declared before it existed."
        )
    t = _tables_for("isv", tax_year)
    b = isv(to_vehicle(vehicle), declaration_date, year=tax_year)
    flags = list(b.flags)
    if declaration_date.year != tax_year:
        flags.append(
            f"declaration_date is in {declaration_date.year} but the {tax_year} tables were "
            f"used; {declaration_date.year} rates may differ"
        )
    return IsvResult(
        total_eur=b.total,
        engine_component_eur=b.engine,
        co2_component_eur=b.co2,
        age_reduction=b.reduction,
        regime=b.regime,
        regime_factor=b.regime_factor,
        minimum_applied=b.minimum_applied,
        particle_surcharge_eur=b.particle_surcharge,
        co2_standard_used=b.co2_standard,
        co2_standard_assumed=b.standard_kind == "estimated",
        alternative_total_eur=b.alternative_total,
        flags=flags,
        tax_year=tax_year,
        declaration_date=declaration_date,
        sources=t["sources"],
    )


def iuc_result(vehicle: VehicleInput, tax_year: int = _tables.CURRENT_YEAR) -> IucResult:
    t = _tables_for("iuc", tax_year)
    v = to_vehicle(vehicle)
    try:
        b = iuc(v, year=tax_year)
    except CategoryANotSupported as e:
        raise ToolError(
            f"IUC category A is not supported: first registered {vehicle.first_registration}, "
            f"before {t['category_b_from']}. This server computes category B only. Tell the "
            "user; do not retry with a different date."
        ) from e
    assumed = vehicle.co2_standard == "unknown" and vehicle.fuel != "electric"
    flags = []
    if assumed:
        flags.append(
            f"CO2 standard assumed to be {b.co2_standard.upper()} from the registration date "
            f"({vehicle.first_registration.year}); confirm it on the certificate of conformity"
        )
    return IucResult(
        total_eur=b.total,
        engine_component_eur=b.engine,
        co2_component_eur=b.co2,
        co2_extra_eur=b.co2_extra,
        year_coefficient=b.coefficient,
        diesel_extra_eur=b.diesel_extra,
        co2_standard_used=b.co2_standard,
        co2_standard_assumed=assumed,
        flags=flags,
        tax_year=tax_year,
        sources=t["sources"],
    )


def register(mcp: MCPServer) -> None:
    @mcp.tool(
        name="calculate_isv",
        title="Calculate ISV (registration tax)",
        description=ISV_DESCRIPTION,
        annotations=READ_ONLY,
    )
    def calculate_isv(
        vehicle: Annotated[VehicleInput, Field(description="The car being registered.")],
        declaration_date: Annotated[
            date,
            Field(
                description="Date the car is declared to the tax authority (ISO 8601). "
                "Sets the age reduction; never defaults to today so results are reproducible."
            ),
        ],
        tax_year: TaxYear = _tables.CURRENT_YEAR,
    ) -> IsvResult:
        return isv_result(vehicle, declaration_date, tax_year)

    @mcp.tool(
        name="calculate_iuc",
        title="Calculate IUC (yearly circulation tax)",
        description=IUC_DESCRIPTION,
        annotations=READ_ONLY,
    )
    def calculate_iuc(
        vehicle: Annotated[VehicleInput, Field(description="The car being taxed.")],
        tax_year: TaxYear = _tables.CURRENT_YEAR,
    ) -> IucResult:
        return iuc_result(vehicle, tax_year)
