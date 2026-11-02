"""The MCP server object. Tools, resources and prompts are registered on it."""

from mcp.server.mcpserver import MCPServer

from pricewise_mcp import __version__, prompts, resources, tax_tools, valuation_tools
from pricewise_mcp.errors import ReadableArgumentErrors

INSTRUCTIONS = (
    "Portugal's vehicle taxes for a used car brought in from another EU/EEA state: "
    "calculate_isv (one-off registration tax) and calculate_iuc (yearly circulation tax). "
    "Also estimate_price_range, a demo of calibrated price ranges trained on synthetic data. "
    "Tax results are illustrations from the 2026 tables, not tax advice: always relay each "
    "result's `flags` and `disclaimer`. Never present estimate_price_range output as the value "
    "of a real car. Tables and their legal sources: pricewise://tables. "
    "What this server does not do: pricewise://limitations."
)

readable_errors = ReadableArgumentErrors()
mcp = MCPServer(
    "pricewise", instructions=INSTRUCTIONS, version=__version__, middleware=[readable_errors]
)
readable_errors.server = mcp

tax_tools.register(mcp)
valuation_tools.register(mcp)
resources.register(mcp)
prompts.register(mcp)
