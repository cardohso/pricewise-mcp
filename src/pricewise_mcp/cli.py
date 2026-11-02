"""Command line entry point: ``pricewise-mcp`` serves over stdio (local clients) or
Streamable HTTP (remote use)."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from pricewise_mcp import __version__
from pricewise_mcp.server import mcp
from pricewise_mcp.valuation_tools import service

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pricewise-mcp",
        description="MCP server for Portuguese vehicle tax (ISV/IUC) and price-range tools.",
    )
    p.add_argument("--version", action="version", version=f"pricewise-mcp {__version__}")
    p.add_argument(
        "--transport",
        choices=["stdio", "http"],
        default="stdio",
        help="stdio for local clients (default); http serves Streamable HTTP at /mcp",
    )
    p.add_argument("--host", default="127.0.0.1", help="http only (default 127.0.0.1)")
    p.add_argument("--port", type=int, default=8000, help="http only (default 8000)")
    return p


def main(argv: Sequence[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    service.warm()  # fit the valuation model while the client connects
    if args.transport == "stdio":
        mcp.run("stdio")
        return
    if args.host not in LOOPBACK:
        print(
            f"warning: serving on {args.host} without authentication; "
            "put it behind a reverse proxy that authenticates callers",
            file=sys.stderr,
        )
    mcp.run(
        "streamable-http",
        host=args.host,
        port=args.port,
        stateless_http=True,
        json_response=True,
    )
