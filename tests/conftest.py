import builtins
import socket

import pytest


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    """Any attempt to resolve a name or open a connection fails the test."""

    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")

    for name in ("getaddrinfo", "create_connection"):
        monkeypatch.setattr(socket, name, refuse)
    for name in ("connect", "connect_ex"):
        monkeypatch.setattr(socket.socket, name, refuse)


@pytest.fixture
def no_file_writes(monkeypatch):
    """Opening a file for writing fails the test."""
    real_open = builtins.open

    def guarded(file, mode="r", *args, **kwargs):
        if any(c in str(mode) for c in "wax+"):
            raise AssertionError(f"file write attempted: {file!r} mode={mode!r}")
        return real_open(file, mode, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", guarded)
