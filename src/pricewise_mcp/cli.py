"""Command line entry point: ``pricewise-mcp`` runs the server over stdio."""

from pricewise_mcp.server import mcp
from pricewise_mcp.valuation_tools import service


def main() -> None:
    service.warm()  # fit the valuation model while the client connects
    mcp.run("stdio")
