"""Prompt templates."""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer


def register(mcp: MCPServer) -> None:
    @mcp.prompt(
        name="explain_tax_breakdown",
        title="Explain a car's tax breakdown",
        description="Compute ISV and IUC for a car and explain each component in plain language.",
    )
    def explain_tax_breakdown(vehicle_description: str, declaration_date: str) -> str:
        return (
            "Explain the Portuguese vehicle tax (ISV and IUC) for this used car brought in from "
            f"another EU/EEA state.\n\nCar: {vehicle_description}\n"
            f"Declaration date: {declaration_date}\n\n"
            "1. Call calculate_isv and calculate_iuc. If a required field is missing "
            "(first registration date, fuel, engine cc, CO2 g/km), ask me for it. Do not guess.\n"
            "2. For each tax, explain the total and its components in plain language: engine, "
            "CO2, age reduction, any minimum or special regime.\n"
            "3. List every entry in `flags` as an assumption I should check.\n"
            "4. Finish with the disclaimer from the result: this is not tax advice."
        )
