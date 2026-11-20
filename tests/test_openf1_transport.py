"""Offline transport tests for respectful OpenF1 API throttling."""
from __future__ import annotations

import io
import json
from urllib.error import HTTPError

import pytest

from apex_f1.openf1_import import _get_json


class Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return io.BytesIO(json.dumps(self.payload).encode("utf-8"))

    def __exit__(self, *_args):
        return False


def test_rate_limit_retries_without_fake_data(monkeypatch):
    calls = []
    waits = []

    def fake_open(request, timeout):
        calls.append(request.full_url)
        if len(calls) < 3:
            raise HTTPError(
                request.full_url, 429, "Too Many Requests", {"Retry-After": "10"}, None
            )
        return Response([{"session_key": 123}])

    monkeypatch.setattr("apex_f1.openf1_import.urlopen", fake_open)
    monkeypatch.setattr("apex_f1.openf1_import.time.sleep", waits.append)
    assert _get_json("sessions", year=2024) == [{"session_key": 123}]
    assert len(calls) == 3
    assert waits == [10.0, 10.0]


def test_non429_error_does_not_retry(monkeypatch):
    called = []

    def fake_open(request, timeout):
        called.append(request.full_url)
        raise HTTPError(request.full_url, 403, "Forbidden", {}, None)

    monkeypatch.setattr("apex_f1.openf1_import.urlopen", fake_open)
    with pytest.raises(RuntimeError, match="HTTP 403"):
        _get_json("sessions", year=2024)
    assert len(called) == 1
