# Demo transcript

Real responses from `pricewise-mcp` over stdio, produced by `examples/demo_client.py`.

## tools/list

```text
calculate_isv: Calculate ISV (registration tax)
calculate_iuc: Calculate IUC (yearly circulation tax)
estimate_price_range: Estimate price range (synthetic demo)
```

## 1. A petrol car, everything known

```json
calculate_isv({
  "vehicle": {
    "first_registration": "2019-06-15",
    "fuel": "petrol",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp"
  },
  "declaration_date": "2026-10-01"
})
```

```json
{
  "total_eur": 211.3,
  "engine_component_eur": 197.45,
  "co2_component_eur": 13.85,
  "age_reduction": 0.65,
  "regime": "normal",
  "regime_factor": 1.0,
  "minimum_applied": false,
  "particle_surcharge_eur": 0.0,
  "co2_standard_used": "wltp",
  "co2_standard_assumed": false,
  "alternative_total_eur": null,
  "flags": [],
  "tax_year": 2026,
  "declaration_date": "2026-10-01",
  "sources": [
    "Código do Imposto sobre Veículos (Lei 22-A/2007), art. 7, tabela A — values unchanged since 2024",
    "Código do ISV, art. 11, tabela D, as amended by Lei 45-A/2024 (Orçamento do Estado 2025): one age-reduction table for both components",
    "Código do ISV, art. 8, as amended by Lei 73-A/2025 (Orçamento do Estado 2026): plug-in hybrid CO2 limit 80 g/km for Euro 6e-bis",
    "Official texts: Diário da República (diariodarepublica.pt); guidance: Autoridade Tributária e Aduaneira (portaldasfinancas.gov.pt)"
  ],
  "disclaimer": "Illustration only, not tax advice. Computed from the 2026 tables of the Código do ISV and Código do IUC; confirm with the Autoridade Tributária e Aduaneira before relying on it."
}
```

## 2. The same car, yearly IUC

```json
calculate_iuc({
  "vehicle": {
    "first_registration": "2019-06-15",
    "fuel": "petrol",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp"
  }
})
```

```json
{
  "total_eur": 111.46,
  "engine_component_eur": 31.77,
  "co2_component_eur": 65.15,
  "co2_extra_eur": 0.0,
  "year_coefficient": 1.15,
  "diesel_extra_eur": 0.0,
  "co2_standard_used": "wltp",
  "co2_standard_assumed": false,
  "flags": [],
  "tax_year": 2026,
  "sources": [
    "Código do Imposto Único de Circulação (Lei 22-A/2007), art. 10 (categoria B), 2026 values",
    "Lei 119/2019: the first registration in the EU/EEA decides the category and the year coefficient",
    "Official texts: Diário da República (diariodarepublica.pt); guidance: Autoridade Tributária e Aduaneira (portaldasfinancas.gov.pt)"
  ],
  "disclaimer": "Illustration only, not tax advice. Computed from the 2026 tables of the Código do ISV and Código do IUC; confirm with the Autoridade Tributária e Aduaneira before relying on it."
}
```

## 3. A diesel with the CO2 standard and particle value unknown: assumptions are flagged

```json
calculate_isv({
  "vehicle": {
    "first_registration": "2020-03-01",
    "fuel": "diesel",
    "engine_cc": 1598,
    "co2_g_km": 115
  },
  "declaration_date": "2026-10-01"
})
```

```json
{
  "total_eur": 1717.64,
  "engine_component_eur": 1107.96,
  "co2_component_eur": 109.68,
  "age_reduction": 0.6,
  "regime": "normal",
  "regime_factor": 1.0,
  "minimum_applied": false,
  "particle_surcharge_eur": 500.0,
  "co2_standard_used": "wltp",
  "co2_standard_assumed": true,
  "alternative_total_eur": null,
  "flags": [
    "CO2 standard (NEDC/WLTP) assumed from the registration date: confirm it on the certificate of conformity",
    "diesel particle value unknown: check field V.5 of the registration document"
  ],
  "tax_year": 2026,
  "declaration_date": "2026-10-01",
  "sources": [
    "Código do Imposto sobre Veículos (Lei 22-A/2007), art. 7, tabela A — values unchanged since 2024",
    "Código do ISV, art. 11, tabela D, as amended by Lei 45-A/2024 (Orçamento do Estado 2025): one age-reduction table for both components",
    "Código do ISV, art. 8, as amended by Lei 73-A/2025 (Orçamento do Estado 2026): plug-in hybrid CO2 limit 80 g/km for Euro 6e-bis",
    "Official texts: Diário da República (diariodarepublica.pt); guidance: Autoridade Tributária e Aduaneira (portaldasfinancas.gov.pt)"
  ],
  "disclaimer": "Illustration only, not tax advice. Computed from the 2026 tables of the Código do ISV and Código do IUC; confirm with the Autoridade Tributária e Aduaneira before relying on it."
}
```

## 4. Price range (synthetic demo data)

```json
estimate_price_range({
  "category": "compact",
  "age_years": 6,
  "usage": 90000,
  "condition": "good"
})
```

```json
{
  "point_eur": 10504.17,
  "range_50": {
    "low_eur": 9362.4,
    "high_eur": 11535.41
  },
  "range_80": {
    "low_eur": 8548.65,
    "high_eur": 12704.31
  },
  "comparables_median_eur": 10190.0,
  "data_source": "synthetic",
  "flags": [],
  "notice": "Trained on synthetic, made-up listings. Prices and ranges say nothing about any real market; they show how the method behaves."
}
```

## 5. A mistake a model is likely to make: the error says how to fix it

```json
calculate_isv({
  "vehicle": {
    "first_registration": "15/06/2019",
    "fuel": "gasoline",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp"
  },
  "declaration_date": "2026-10-01"
})
```

Error result:

```text
Invalid arguments for calculate_isv. Fix these and call again:
- vehicle.first_registration: input should be a valid date or datetime, invalid character in year (got '15/06/2019'). Hint: dates are YYYY-MM-DD; if '15/06/2019' is day/month/year, send '2019-06-15'
- vehicle.fuel: input should be 'petrol', 'diesel', 'hybrid', 'plugin_hybrid' or 'electric' (got 'gasoline'). Hint: use 'petrol' for 'gasoline'
```

## 6. A car the server cannot compute

```json
calculate_iuc({
  "vehicle": {
    "first_registration": "2005-01-01",
    "fuel": "petrol",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp"
  }
})
```

Error result:

```text
Error executing tool calculate_iuc: IUC category A is not supported: first registered 2005-01-01, before 2007-07-01. This server computes category B only. Tell the user; do not retry with a different date.
```

## Resource: pricewise://limitations

```markdown
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
```

## Prompt: explain_tax_breakdown

```text
Explain the Portuguese vehicle tax (ISV and IUC) for this used car brought in from another EU/EEA state.

Car: 2019 petrol, 1199 cc, 125 g/km WLTP
Declaration date: 2026-10-01

1. Call calculate_isv and calculate_iuc. If a required field is missing (first registration date, fuel, engine cc, CO2 g/km), ask me for it. Do not guess.
2. For each tax, explain the total and its components in plain language: engine, CO2, age reduction, any minimum or special regime.
3. List every entry in `flags` as an assumption I should check.
4. Finish with the disclaimer from the result: this is not tax advice.
```

