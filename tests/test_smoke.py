import anyio
from mcp.client import Client

from pricewise_mcp.server import mcp


def test_server_starts_and_answers_in_process():
    async def run():
        async with Client(mcp) as client:
            return await client.list_tools()

    assert anyio.run(run).tools == []  # tools arrive in step 3
