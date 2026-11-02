import socket

import pytest


def test_outside_hosts_are_refused():
    with pytest.raises(AssertionError, match="network access attempted"):
        socket.getaddrinfo("example.com", 80)
    with pytest.raises(AssertionError, match="network access attempted"):
        socket.socket().connect(("93.184.216.34", 80))
