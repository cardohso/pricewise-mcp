import anyio
from mcp.client import Client

from pricewise_mcp.server import mcp


def with_client(fn):
    """Run ``fn(client)`` against the in-process server and return its result."""

    async def run():
        async with Client(mcp) as client:
            return await fn(client)

    return anyio.run(run)
