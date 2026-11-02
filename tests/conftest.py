import builtins
import socket

import pytest

LOOPBACK = {"127.0.0.1", "::1", "localhost", None}


def _is_local(address) -> bool:
    return isinstance(address, str) or address[0] in LOOPBACK  # unix socket or loopback


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Only loopback is reachable: any other name lookup or connection fails the test."""
    real_connect, real_connect_ex, real_lookup = (
        socket.socket.connect,
        socket.socket.connect_ex,
        socket.getaddrinfo,
    )

    def guard(real):
        def guarded(self, address, *args):
            if not _is_local(address):
                raise AssertionError(f"network access attempted: {address!r}")
            return real(self, address, *args)

        return guarded

    def lookup(host, *args, **kwargs):
        if host not in LOOPBACK:
            raise AssertionError(f"network access attempted: lookup of {host!r}")
        return real_lookup(host, *args, **kwargs)

    monkeypatch.setattr(socket.socket, "connect", guard(real_connect))
    monkeypatch.setattr(socket.socket, "connect_ex", guard(real_connect_ex))
    monkeypatch.setattr(socket, "getaddrinfo", lookup)


@pytest.fixture
def no_file_writes(monkeypatch):
    """Opening a file for writing fails the test."""
    real_open = builtins.open

    def guarded(file, mode="r", *args, **kwargs):
        if any(c in str(mode) for c in "wax+"):
            raise AssertionError(f"file write attempted: {file!r} mode={mode!r}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)
