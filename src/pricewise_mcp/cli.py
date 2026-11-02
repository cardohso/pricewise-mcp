"""Command line entry point: ``pricewise-mcp`` runs the server over stdio."""

from pricewise_mcp.server import mcp


def main() -> None:
    mcp.run("stdio")
