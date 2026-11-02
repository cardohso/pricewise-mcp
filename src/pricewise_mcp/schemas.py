"""Typed inputs and outputs shared by the tools. The descriptions are what an
MCP client (and the model behind it) reads, so they say what each field means
and where to find it on the vehicle documents."""

from __future__ import annotations

from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

DISCLAIMER = (
    "Illustration only, not tax advice. Computed from the 2026 tables of the Código do ISV "
    "and Código do IUC; confirm with the Autoridade Tributária e Aduaneira before relying on it."
)

FuelType = Literal["petrol", "diesel", "hybrid", "plugin_hybrid", "electric"]


class VehicleInput(BaseModel):
    """A used passenger car brought into Portugal from another EU/EEA state."""

    model_config = ConfigDict(extra="forbid")

    first_registration: Annotated[
        date,
        Field(
            description="Date of first registration anywhere in the EU/EEA (ISO 8601, "
            "e.g. 2019-06-15). Document field B of the registration certificate."
        ),
    ]
    fuel: Annotated[
        FuelType,
        Field(description="Fuel type. 'hybrid' is a non-plug-in hybrid."),
    ]
    engine_cc: Annotated[
        int | None,
        Field(
            ge=50,
            le=10_000,
            description="Engine displacement in cm3 (field P.1). "
            "Required unless fuel is 'electric'.",
        ),
    ] = None
    co2_g_km: Annotated[
        float | None,
        Field(
            ge=0,
            le=600,
            description="Combined CO2 in g/km from the certificate of conformity (field V.7). "
            "Required unless fuel is 'electric'.",
        ),
    ] = None
    co2_standard: Annotated[
        Literal["nedc", "wltp", "unknown"],
        Field(
            description="Test standard behind co2_g_km. If 'unknown', it is assumed from the "
            "registration date and the result carries a flag saying so."
        ),
    ] = "unknown"
    euro_norm: Annotated[
        str | None,
        Field(
            description="Euro emissions class such as '6d' or '6e-bis'. "
            "Matters for plug-in hybrids."
        ),
    ] = None
    particles_g_km: Annotated[
        float | None,
        Field(
            ge=0,
            le=1,
            description="Diesel particle emissions in g/km (field V.5). If omitted for a diesel, "
            "the surcharge is assumed due and the result carries a flag.",
        ),
    ] = None
    electric_range_km: Annotated[
        int | None,
        Field(
            ge=0,
            le=2_000,
            description="Electric range in km; hybrids need at least 50 for the reduced regime.",
        ),
    ] = None
    hybrid_base_fuel: Annotated[
        Literal["petrol", "diesel"],
        Field(description="For hybrids: which fuel's CO2 table applies."),
    ] = "petrol"

    @model_validator(mode="after")
    def _combustion_needs_engine_and_co2(self) -> VehicleInput:
        if self.fuel != "electric":
            missing = [
                f"{name} (field {doc})"
                for name, doc in (("engine_cc", "P.1"), ("co2_g_km", "V.7"))
                if getattr(self, name) is None
            ]
            if missing:
                raise ValueError(
                    f"missing {' and '.join(missing)}, required when fuel is '{self.fuel}' "
                    "(only electric cars may omit them). Ask the user; do not estimate"
                )
        return self


class IsvResult(BaseModel):
    total_eur: float = Field(description="ISV due, in euros, rounded half-up to the cent.")
    engine_component_eur: float = Field(
        description="Engine-size component after age reduction and regime factor."
    )
    co2_component_eur: float = Field(
        description="CO2 component after age reduction and regime factor."
    )
    age_reduction: float = Field(description="Age reduction applied, 0.10 to 0.80.")
    regime: Literal["normal", "electric", "plugin_hybrid", "hybrid"]
    regime_factor: float = Field(description="Multiplier for the reduced hybrid regimes.")
    minimum_applied: bool = Field(
        description="True if the legal minimum replaced the computed value."
    )
    particle_surcharge_eur: float
    co2_standard_used: Literal["nedc", "wltp"]
    co2_standard_assumed: bool = Field(
        description="True if the standard was guessed from the registration date."
    )
    alternative_total_eur: float | None = Field(
        description="Total under the other standard, when the standard was unknown "
        "and both are possible."
    )
    flags: list[str] = Field(
        description="Assumptions and caveats the caller should relay to the user."
    )
    tax_year: int
    declaration_date: date
    sources: list[str] = Field(description="Legal sources of the tables used.")
    disclaimer: str = DISCLAIMER


class IucResult(BaseModel):
    total_eur: float = Field(description="IUC for one year, in euros, rounded half-up to the cent.")
    engine_component_eur: float
    co2_component_eur: float
    co2_extra_eur: float = Field(description="Extra for high CO2 (cars registered from 2017).")
    year_coefficient: float = Field(
        description="Coefficient set by the year of first registration."
    )
    diesel_extra_eur: float
    co2_standard_used: Literal["nedc", "wltp"]
    co2_standard_assumed: bool
    flags: list[str]
    tax_year: int
    sources: list[str]
    disclaimer: str = DISCLAIMER
