"""The MCP server object. Tools, resources and prompts are registered on it."""

from mcp.server.mcpserver import MCPServer

from pricewise_mcp import __version__, tax_tools

INSTRUCTIONS = (
    "Portuguese vehicle tax (ISV, IUC) and price-range estimates. Tax results are "
    "illustrations from the 2026 tables, not tax advice. Price estimates come from a "
    "model trained on synthetic data."
)

mcp = MCPServer("pricewise", instructions=INSTRUCTIONS, version=__version__)

tax_tools.register(mcp)
