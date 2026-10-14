"""T3: tests/omr must not touch the network.

Every test here runs with outbound socket connections blocked;
test_omr_guards.py proves the guard catches a deliberate connection attempt
before any "no network" result is trusted (T5).
"""
import socket

import pytest


class NetworkBlocked(RuntimeError):
    pass


@pytest.fixture(autouse=True)
def _no_network(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise NetworkBlocked("network disabled in tests/omr")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket.socket, "connect_ex", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
