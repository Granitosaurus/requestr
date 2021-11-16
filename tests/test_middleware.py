import pytest
from requestr.middlewares import (RandomUserAgent, RetryExceptions,
                                  RetryStatuses)
from requestr.request import Request


def test_add_RetryExceptions():
    combined = RetryExceptions(ValueError, KeyError, times=3, sleep=5) + RetryExceptions(IndexError, NameError)
    assert combined.exceptions == (ValueError, KeyError, IndexError, NameError)
    assert combined.times == 3
    assert combined.sleep == 5


def test_add_RetryStatuses():
    combined = RetryStatuses(500, 502, times=3, sleep=5) + RetryStatuses(503, 504)
    assert combined.statuses == (500, 502, 503, 504)
    assert combined.times == 3
    assert combined.sleep == 5


@pytest.mark.asyncio
async def test_RandomUserAgent(mocker):
    mw = RandomUserAgent("foo", "bar", "gaz", "fla")
    for rand in ["bar", "bar", "gaz", "foo", "fla"]:
        mocker.patch("random.choice", lambda v: rand)
        req = Request("http://httpbin.org/")
        await mw.request(req, None, None)
        assert req.headers == {"User-Agent": rand}
