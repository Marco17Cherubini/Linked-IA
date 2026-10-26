from datetime import date

import pytest
import requests

from linkedia.domain.markets import MARKETS
from linkedia.errors import ProviderUnavailable
from linkedia.providers.http import request_json
from linkedia.providers.llm import DeepSeekClient
from linkedia.providers.market_data import parse_chart_response


def chart(timestamps, closes, tz="America/New_York", error=None):
    return {"chart": {"error": error, "result": [{
        "meta": {"exchangeTimezoneName": tz},
        "timestamp": timestamps,
        "indicators": {"quote": [{"open": closes, "high": closes, "low": closes, "close": closes,
                                  "volume": [1] * len(closes)}]},
    }]}}


def test_chart_dates_are_local_to_exchange():
    # 1299024000 = 2011-03-02 00:00 UTC = 09:00 a Tokyo
    bars = parse_chart_response(chart([1299024000], [10492.38], "Asia/Tokyo"), MARKETS["NIKKEI"])
    assert bars[0].date == date(2011, 3, 2)


def test_chart_keeps_missing_close_as_none():
    bars = parse_chart_response(chart([1299024000, 1299110400], [None, 5.0]), MARKETS["SP500"])
    assert bars[0].close is None and bars[1].close == 5.0


def test_chart_error_is_provider_failure_not_empty():
    with pytest.raises(ProviderUnavailable):
        parse_chart_response(chart([], [], error={"code": "Not Found"}), MARKETS["SP500"])
    with pytest.raises(ProviderUnavailable):
        parse_chart_response({"unexpected": True}, MARKETS["SP500"])


def test_chart_rejects_misaligned_columns():
    payload = chart([1, 2], [1.0])
    with pytest.raises(ProviderUnavailable):
        parse_chart_response(payload, MARKETS["SP500"])


class FakeResponse:
    def __init__(self, status, body=None):
        self.status_code = status
        self._body = body

    def json(self):
        if self._body is None:
            raise ValueError("no json")
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.headers = {}

    def request(self, method, url, **kwargs):
        self.calls.append(kwargs)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def test_request_json_retries_transient_errors_with_timeout():
    session = FakeSession([requests.Timeout(), FakeResponse(503), FakeResponse(200, {"ok": 1})])
    assert request_json(session, "GET", "u", provider="P", timeout=3, backoff=0) == {"ok": 1}
    assert all(c["timeout"] == 3 for c in session.calls)


def test_request_json_does_not_retry_client_errors():
    session = FakeSession([FakeResponse(401)])
    with pytest.raises(ProviderUnavailable, match="HTTP 401"):
        request_json(session, "GET", "u", provider="P", timeout=3, backoff=0)
    assert len(session.calls) == 1


def test_request_json_gives_up():
    session = FakeSession([FakeResponse(429)] * 3)
    with pytest.raises(ProviderUnavailable):
        request_json(session, "GET", "u", provider="P", timeout=3, retries=2, backoff=0)


def test_deepseek_invalid_content_is_an_error():
    session = FakeSession([FakeResponse(200, {"choices": [{"message": {"content": "non json"}}]})])
    client = DeepSeekClient("k", base_url="https://x", model="m", session=session)
    with pytest.raises(ProviderUnavailable):
        client.complete_json("s", "u", max_tokens=10)


def test_deepseek_parses_json_object():
    body = {"choices": [{"message": {"content": '{"headline": "x"}'}}], "usage": {"total_tokens": 5}}
    session = FakeSession([FakeResponse(200, body)])
    client = DeepSeekClient("k", base_url="https://x", model="m", session=session)
    data, usage = client.complete_json("s", "u", max_tokens=10)
    assert data == {"headline": "x"} and usage["total_tokens"] == 5
