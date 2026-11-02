"""A real MCP client talking to the server over stdio. Prints a Markdown transcript of
every tool, one resource and the prompt, with the server's actual responses.

    python examples/demo_client.py > docs/demo-transcript.md
"""

import json
import sys

import anyio
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

PETROL = {
    "first_registration": "2019-06-15",
    "fuel": "petrol",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp",
}
DIESEL = {"first_registration": "2020-03-01", "fuel": "diesel", "engine_cc": 1598, "co2_g_km": 115}

STEPS = [
    (
        "1. A petrol car, everything known",
        "calculate_isv",
        {"vehicle": PETROL, "declaration_date": "2026-10-01"},
    ),
    ("2. The same car, yearly IUC", "calculate_iuc", {"vehicle": PETROL}),
    (
        "3. A diesel with the CO2 standard and particle value unknown: assumptions are flagged",
        "calculate_isv",
        {"vehicle": DIESEL, "declaration_date": "2026-10-01"},
    ),
    (
        "4. Price range (synthetic demo data)",
        "estimate_price_range",
        {"category": "compact", "age_years": 6, "usage": 90000, "condition": "good"},
    ),
    (
        "5. A mistake a model is likely to make: the error says how to fix it",
        "calculate_isv",
        {
            "vehicle": {**PETROL, "fuel": "gasoline", "first_registration": "15/06/2019"},
            "declaration_date": "2026-10-01",
        },
    ),
    (
        "6. A car the server cannot compute",
        "calculate_iuc",
        {"vehicle": {**PETROL, "first_registration": "2005-01-01"}},
    ),
]


def block(lang, text):
    return f"```{lang}\n{text}\n```\n"


async def main():
    params = StdioServerParameters(command=sys.executable, args=["-m", "pricewise_mcp"])
    out = [
        "# Demo transcript\n",
        "Real responses from `pricewise-mcp` over stdio, produced by `examples/demo_client.py`.\n",
    ]
    async with Client(params) as client:
        tools = (await client.list_tools()).tools
        out.append("## tools/list\n")
        out.append(block("text", "\n".join(f"{t.name}: {t.title}" for t in tools)))
        for title, name, args in STEPS:
            out.append(f"## {title}\n")
            out.append(block("json", f"{name}({json.dumps(args, indent=2)})"))
            r = await client.call_tool(name, args)
            if r.is_error:
                out.append("Error result:\n")
                out.append(block("text", r.content[0].text))
            else:
                out.append(
                    block("json", json.dumps(r.structured_content, indent=2, ensure_ascii=False))
                )
        out.append("## Resource: pricewise://limitations\n")
        res = await client.read_resource("pricewise://limitations")
        out.append(block("markdown", res.contents[0].text.strip()))
        out.append("## Prompt: explain_tax_breakdown\n")
        p = await client.get_prompt(
            "explain_tax_breakdown",
            {
                "vehicle_description": "2019 petrol, 1199 cc, 125 g/km WLTP",
                "declaration_date": "2026-10-01",
            },
        )
        out.append(block("text", p.messages[0].content.text))
    print("\n".join(out))


anyio.run(main)
