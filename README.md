# pricewise-mcp

[![ci](https://github.com/cardohso/pricewise-mcp/actions/workflows/ci.yml/badge.svg)](https://github.com/cardohso/pricewise-mcp/actions/workflows/ci.yml)

An [MCP](https://modelcontextprotocol.io) server that lets Claude Desktop, Claude Code or any
MCP client compute **Portuguese vehicle taxes** (ISV and IUC) and **price ranges**, using the
tested code in [pricewise-pt](https://github.com/cardohso/pricewise-pt).

## In 30 seconds

- Three tools: `calculate_isv`, `calculate_iuc`, `estimate_price_range`.
- Deterministic: same input, same output. No network calls and no file writes; the tests block
  all non-loopback network access and fail if a tool path opens a file for writing. The tax arithmetic lives in pricewise-pt, written from the legal articles and
  checked against hand-worked examples; this server adds typed inputs, validation, sources and
  error messages a language model can act on.
- Every tax answer lists its **assumptions** (`flags`), its **legal sources** and a
  **not-tax-advice** disclaimer.
- The price tool is a **demo on synthetic data**, labelled as such in every answer.
- Resources for the versioned tax tables and a limitations document, plus one prompt.
- stdio for local clients, Streamable HTTP for remote use.

Real transcript of every tool: [docs/demo-transcript.md](docs/demo-transcript.md).

## Install and connect

Needs [uv](https://docs.astral.sh/uv/). Nothing is published to PyPI; the commands install
straight from GitHub.

**1. Install once**

```bash
uv tool install git+https://github.com/cardohso/pricewise-mcp
pricewise-mcp --version    # run it once now: the first launch is slow, later ones take seconds
```

Install once instead of launching with `uvx --from git+...`: `uvx` contacts GitHub on
start and rebuilds the package after the repo changes, and a cold start can exceed the 30-second connect timeout
Claude Code applies (this happened while testing). The installed command starts offline. To
update later: `uv tool upgrade pricewise-mcp`.

**2. Connect a client**

*Claude Code*

```bash
claude mcp add pricewise -- pricewise-mcp
```

*Claude Desktop*: add to `claude_desktop_config.json` (Settings, Developer, Edit Config):

```json
{
  "mcpServers": {
    "pricewise": {
      "command": "pricewise-mcp"
    }
  }
}
```

Claude Desktop may not find the command on its PATH. If the server does not start, put the
full path from `which pricewise-mcp` in `"command"`.

*Streamable HTTP* (remote or shared use):

```bash
pricewise-mcp --transport http --port 8000
claude mcp add --transport http pricewise http://127.0.0.1:8000/mcp
```

HTTP is stateless, answers in JSON and binds to `127.0.0.1` by default. The server has **no
authentication**; if you bind another address it warns on stderr. Put it behind a reverse proxy
that authenticates callers before exposing it.

*No install* (slower and more fragile): replace `pricewise-mcp` in the commands above with
`uvx --from git+https://github.com/cardohso/pricewise-mcp pricewise-mcp`.

**From a clone**

```bash
git clone https://github.com/cardohso/pricewise-mcp && cd pricewise-mcp
python -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/pricewise-mcp --version
```

The first valuation call after the server starts can take up to about 20 seconds: the model is
fitted in a background thread at launch.

## Tools

All three are read-only, idempotent and closed-world (tool annotations). Responses are
structured JSON matching the tool's output schema. Examples below are real server output;
`sources` and `disclaimer` are shortened here and complete in the
[transcript](docs/demo-transcript.md).

### `calculate_isv`

The one-off registration tax for a used passenger car brought in from another EU/EEA state.

Input: a `vehicle` (first registration date, fuel, engine cc, CO2 g/km, CO2 test standard, and
optional Euro class, diesel particles, electric range, hybrid base fuel), a required
`declaration_date`, and an optional `tax_year`.

```json
{"vehicle": {"first_registration": "2019-06-15", "fuel": "petrol", "engine_cc": 1199,
             "co2_g_km": 125, "co2_standard": "wltp"},
 "declaration_date": "2026-10-01"}
```

```json
{
  "total_eur": 211.3,
  "engine_component_eur": 197.45,
  "co2_component_eur": 13.85,
  "age_reduction": 0.65,
  "regime": "normal",
  "minimum_applied": false,
  "co2_standard_used": "wltp",
  "co2_standard_assumed": false,
  "flags": [],
  "tax_year": 2026,
  "sources": ["Código do Imposto sobre Veículos (Lei 22-A/2007), art. 7, tabela A ...", "..."],
  "disclaimer": "Illustration only, not tax advice. ..."
}
```

With the CO2 standard and a diesel's particle value left out, the same call still answers, with
the costlier assumption made explicit:

```json
{
  "total_eur": 1717.64,
  "particle_surcharge_eur": 500.0,
  "co2_standard_assumed": true,
  "flags": [
    "CO2 standard (NEDC/WLTP) assumed from the registration date: confirm it on the certificate of conformity",
    "diesel particle value unknown: check field V.5 of the registration document"
  ]
}
```

(Other fields omitted. Input: a 2020-03-01 diesel, 1598 cc, 115 g/km.)

### `calculate_iuc`

One year of the yearly circulation tax for a category B car (first registered on or after
1 July 2007). Same `vehicle` object; optional `tax_year`.

```json
{"vehicle": {"first_registration": "2019-06-15", "fuel": "petrol", "engine_cc": 1199,
             "co2_g_km": 125, "co2_standard": "wltp"}}
```

```json
{"total_eur": 111.46, "engine_component_eur": 31.77, "co2_component_eur": 65.15,
 "co2_extra_eur": 0.0, "year_coefficient": 1.15, "diesel_extra_eur": 0.0,
 "co2_standard_assumed": false, "flags": [], "tax_year": 2026}
```

(`sources` and `disclaimer` omitted.) Cars registered before July 2007 get an error.

### `estimate_price_range`

A used-car asking price with a 50% and an 80% range. **Trained on synthetic, made-up listings:
it demonstrates calibrated uncertainty and says nothing about a real car or market.** Input:
`category` (`compact`, `hatchback`, `crossover`, `estate`, `electric`), `age_years`, `usage`
(km), optional `condition`.

```json
{"category": "compact", "age_years": 6, "usage": 90000, "condition": "good"}
```

```json
{
  "point_eur": 10504.17,
  "range_50": {"low_eur": 9362.4, "high_eur": 11535.41},
  "range_80": {"low_eur": 8548.65, "high_eur": 12704.31},
  "comparables_median_eur": 10190.0,
  "data_source": "synthetic",
  "flags": [],
  "notice": "Trained on synthetic, made-up listings. ..."
}
```

Inputs outside the synthetic training range add an extrapolation flag.

### What a wrong call looks like

```text
Invalid arguments for calculate_isv. Fix these and call again:
- vehicle.first_registration: input should be a valid date or datetime, invalid character in year (got '15/06/2019'). Hint: dates are YYYY-MM-DD; if '15/06/2019' is day/month/year, send '2019-06-15'
- vehicle.fuel: input should be 'petrol', 'diesel', 'hybrid', 'plugin_hybrid' or 'electric' (got 'gasoline'). Hint: use 'petrol' for 'gasoline'
```

## Resources and prompt

| URI | What |
|---|---|
| `pricewise://tables` | Index of the available table years, with legal sources |
| `pricewise://tables/isv/2026` | The ISV rate tables exactly as the calculator uses them |
| `pricewise://tables/iuc/2026` | The IUC rate tables |
| `pricewise://limitations` | What the server does not do |

Prompt `explain_tax_breakdown(vehicle_description, declaration_date)`: tells the model to call
both tax tools, ask for missing fields instead of guessing, explain each component, list the
flags and finish with the disclaimer.

## Design decisions

- **Deterministic tools only.** A model is good at conversation and bad at arithmetic on legal
  tables. These tools do the arithmetic; the model only gathers inputs and explains outputs.
  All tax logic stays in pricewise-pt, the server is a thin typed layer.
- **`declaration_date` is required.** ISV depends on the car's age on that date. A hidden
  default of "today" would make results change silently, so the model must pass it.
- **Assumptions are data.** Instead of refusing when the CO2 standard or a diesel's particle
  value is unknown, ISV computes the costlier case and returns the assumption in `flags`, with
  the other standard's total in `alternative_total_eur` where both apply. IUC assumes the
  standard from the registration year and flags it. Tool descriptions tell
  the model to relay flags; engine size and CO2 are never guessed (the model is told to ask).
- **Structured output plus provenance.** Every tax result carries `sources` (the articles the
  tables come from) and the disclaimer, so they survive however the model paraphrases.
- **Errors written for a model, not a developer.** pydantic's raw text (internal names, the
  echoed input, a docs URL) is replaced by one line per problem with the field, the value sent
  and a hint for common mistakes (`gasoline`, day/month/year dates, litres for cm3). Domain
  errors say whether retrying makes sense. Unknown top-level arguments are rejected: the SDK
  would otherwise drop a misspelt optional argument silently.
- **One nested `vehicle` object** shared by the tax tools, so the model fills the same shape
  every time and a future multi-vehicle tool can reuse it.
- **No `compare_costs` tool.** A model can call the two tools and add the results. A multi-year
  total would assume today's IUC rates and coefficients hold for N years, which is false, and
  would look more precise than it is.
- **Synthetic valuation, labelled everywhere.** The model is fitted at startup from
  pricewise-pt's generator (about 15 s), so no data file ships and the output is reproducible.
- **Stateless HTTP.** No sessions to store; any instance can answer any request.
- **Pinned library.** pricewise-pt is not on PyPI, so it is pinned to a commit in
  `pyproject.toml` and its tax tests remain the source of truth.

## Limitations

Short version; the full text is the `pricewise://limitations` resource.

- **Not tax advice.** 2026 tables only; confirm with the Autoridade Tributária e Aduaneira.
- Used passenger cars from another EU/EEA state. Not covered: imports from outside the EU/EEA,
  commercial vehicles, motorcycles, exemptions beyond the hybrid regimes in the tables.
- IUC is one year at the table year's rates; category A (before July 2007) is rejected.
- The price model is trained on synthetic data and its ranges are calibrated only on that data.
- HTTP has no authentication.
- Tested with the MCP Python SDK's client over stdio and HTTP (in CI), and by hand in Claude
  Code (2 November 2026): asked for the ISV and IUC of the 2019 petrol car above and for a
  compact's price range, Claude called the three tools and reported €211.30, €111.46 and the
  synthetic range, with components, the disclaimer and the synthetic-data warning. That session
  also showed the cold-start timeout described under Install. The Claude Desktop snippet follows
  its documented format and has not been run.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q          # about 30 s: the valuation model is fitted a few times
python examples/demo_client.py > docs/demo-transcript.md   # regenerate the transcript
```

The tests run offline (only loopback is reachable), assert no file is opened for
writing in the ISV, IUC and valuation paths, list the tools through an in-process client, start the server as a real subprocess
over stdio and HTTP, and reuse the hand-worked ISV and IUC cases from pricewise-pt as golden
values.

## Licence

MIT, see [LICENSE](LICENSE).
