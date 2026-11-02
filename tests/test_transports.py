"""The server as a separate process, reached the way Claude Desktop (stdio) or a remote
client (HTTP) would reach it."""

import json
import socket
import subprocess
import sys
import time

import anyio
import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters

VEHICLE = {
    "first_registration": "2019-06-15",
    "fuel": "petrol",
    "engine_cc": 1199,
    "co2_g_km": 125,
    "co2_standard": "wltp",
}
TOOLS = {"calculate_isv", "calculate_iuc", "estimate_price_range"}


async def exercise(client):
    """Call every tool and read a resource; return what came back."""
    tools = {t.name for t in (await client.list_tools()).tools}
    isv = await client.call_tool(
        "calculate_isv", {"vehicle": VEHICLE, "declaration_date": "2026-10-01"}
    )
    iuc = await client.call_tool("calculate_iuc", {"vehicle": VEHICLE})
    price = await client.call_tool(
        "estimate_price_range",
        {"category": "compact", "age_years": 6, "usage": 90_000, "condition": "good"},
    )
    table = await client.read_resource("pricewise://tables/isv/2026")
    return tools, isv, iuc, price, json.loads(table.contents[0].text)


def check(result):
    tools, isv, iuc, price, table = result
    assert tools >= TOOLS
    assert isv.structured_content["total_eur"] == 211.30
    assert iuc.structured_content["total_eur"] == 111.46
    assert price.structured_content["data_source"] == "synthetic"
    assert table["year"] == 2026


def test_stdio_subprocess_serves_every_tool():
    params = StdioServerParameters(command=sys.executable, args=["-m", "pricewise_mcp"])

    async def run():
        with anyio.fail_after(120):
            async with Client(params) as client:
                return await exercise(client)

    check(anyio.run(run))


@pytest.fixture
def http_server():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    proc = subprocess.Popen(
        [sys.executable, "-m", "pricewise_mcp", "--transport", "http", "--port", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if proc.poll() is not None:
                raise AssertionError(f"server exited early: {proc.stderr.read()}")
            try:
                socket.create_connection(("127.0.0.1", port), timeout=0.5).close()
                break
            except OSError:
                time.sleep(0.3)
        else:
            raise AssertionError("server did not start listening")
        yield f"http://127.0.0.1:{port}/mcp"
    finally:
        proc.terminate()
        proc.wait(timeout=10)


def test_streamable_http_serves_every_tool(http_server):
    async def run():
        with anyio.fail_after(120):
            async with Client(http_server) as client:
                return await exercise(client)

    check(anyio.run(run))
