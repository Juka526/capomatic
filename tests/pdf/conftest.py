"""Block all network use in PDF tests; any attempt fails the test that made it."""
import socket

import pytest


class NetworkAttempt(AssertionError):
    pass


@pytest.fixture(autouse=True)
def no_network(monkeypatch):
    attempts = []

    def deny(*args, **kwargs):
        attempts.append(args[1:2])
        raise NetworkAttempt("network blocked in tests/pdf")

    monkeypatch.setattr(socket.socket, "connect", lambda self, *a, **k: deny(self, *a))
    monkeypatch.setattr(socket.socket, "connect_ex", lambda self, *a, **k: deny(self, *a))
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: deny(None, *a))
    yield attempts
    assert not attempts, f"network attempted: {attempts}"
