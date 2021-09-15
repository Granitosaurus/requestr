import pytest
import asyncio
import pickle
from aiohttp import BasicAuth
from aiohttp.client_exceptions import ClientConnectionError
from requestr import Request, Response, Session
from requestr.downloader import Downloader
from requestr.middlewares import Middleware
from requestr.exceptions import RequestFailed, MwareRedirectLimit
from requestr.middlewares import RetryStatuses


@pytest.mark.asyncio
async def test_downloader_html(httpbin):
    dl = Downloader()
    req = Request(httpbin.url + "/html")
    resp = await dl.send(req)
    assert req.url == resp.url
    assert resp.request is req
    assert resp.text
    assert resp.content


@pytest.mark.asyncio
async def test_downloader_200(httpbin):
    dl = Downloader()
    req = Request(httpbin.url + "/status/200")
    resp = await dl.send(req)
    assert isinstance(resp, Response)
    assert resp.status == 200
    assert resp.text == ""
    assert resp.request == req
    assert resp.url == req.url


@pytest.mark.asyncio
async def test_downloader_concurrent_request(httpbin):
    dl = Downloader()
    default_slot = httpbin.url.split("://", 1)[1].split(":")[0]
    resps = await asyncio.gather(
        dl.send(Request(httpbin.url + "/status/200")),
        dl.send(Request(httpbin.url + "/status/200")),
        dl.send(Request(httpbin.url + "/status/200")),
        dl.send(Request(httpbin.url + "/status/200")),
        dl.send(Request(httpbin.url + "/status/200")),
    )
    assert len(resps) == 5
    assert list(dl.sessions) == [default_slot]
    assert dl.stats == {
        "req/scheduled": 5,
        "req/sent": 5,
        "session/new": 1,
    }

    dl = Downloader()
    resps = await asyncio.gather(
        dl.send(Request(httpbin.url + "/status/500")),
        dl.send(Request(httpbin.url + "/status/500", slot="custom")),
        dl.send(Request(httpbin.url + "/status/500")),
        return_exceptions=True,
    )
    assert dl.stats == {
        "req/scheduled": 3,
        "req/sent": 9,
        "req/retry": 6,
        "sleep/elapsed": 12,
        "respmid/return/req": 6,
        "session/new": 2,
    }


@pytest.mark.asyncio
async def test_downloader_session_select(httpbin):
    dl = Downloader()
    default_slot = httpbin.url.split("://", 1)[1].split(":")[0]
    # first request will establish default session slot
    resp = await dl.send(Request(httpbin.url + "/status/200"))
    assert resp.request.slot == default_slot
    assert list(dl.sessions) == [default_slot]
    # the second request explicitly asks for new session slot
    resp = await dl.send(Request(httpbin.url + "/status/200", slot="new_session"))
    assert resp.request.slot == "new_session"
    assert list(dl.sessions) == [default_slot, "new_session"]


@pytest.mark.asyncio
async def test_downloader_default_custom_fail(httpbin):
    dl = Downloader()
    with pytest.raises(RequestFailed):
        resp = await dl.send(Request(httpbin.url + "/status/404"), mwares={0: RetryStatuses((404, 500))})
    assert dl.stats == {
        "req/retry": 2,
        "req/scheduled": 1,
        "req/sent": 3,
        "respmid/return/req": 2,
        "session/new": 1,
        "sleep/elapsed": 4,
    }
    dl = Downloader()
    resp = await dl.send(Request(httpbin.url + "/status/403"))
    assert resp.status == 403
    assert dl.stats == {
        "req/scheduled": 1,
        "req/sent": 1,
        "session/new": 1,
    }


@pytest.mark.asyncio
async def test_downloader_status_fail_with_default_mwares(httpbin):
    dl = Downloader()
    with pytest.raises(RequestFailed):
        resp = await dl.send(Request(httpbin.url + "/status/500"))
    # ensure default handlers work as they do
    assert dl.stats == {
        "req/retry": 2,
        "req/scheduled": 1,
        "req/sent": 3,
        "respmid/return/req": 2,
        "session/new": 1,
        "sleep/elapsed": 4,
    }

@pytest.mark.asyncio
async def test_downloader_exc_fail():
    # default behavior is to raise all exceptions
    dl = Downloader()
    with pytest.raises(ClientConnectionError):
        resp = await dl.send(Request("http://doesnotexist-for-sure.io/"), mwares={})
    assert dl.stats == {
        "req/scheduled": 1,
        "session/new": 1,
    }

@pytest.mark.asyncio
async def test_downloader_exc_fail_with_default_mwares():
    # with mwares some exceptions should be retried
    dl = Downloader()
    with pytest.raises(RequestFailed):
        resp = await dl.send(Request("http://doesnotexist-for-sure.io/"))
    assert dl.stats == {
        "req/scheduled": 1,
        "req/retry": 2,
        "respmid/exc/req": 2,
        "sleep/elapsed": 4,
        "session/new": 1,
    }

@pytest.mark.asyncio
async def test_downloader_proxy(httpbin):
    dl = Downloader()
    # TODO hide secrets
    resp = await dl.send(
        Request(
            "http://httpbin.org/ip",
            proxy="http://209.127.191.180:9279",
            proxy_auth=BasicAuth("zexfwvoa", "msg7udkifi4j"),
        )
    )
    assert resp.json == {"origin": "209.127.191.180"}

    resp = await dl.send(
        Request(
            "http://httpbin.org/ip",
        )
    )
    assert resp.json != {"origin": "209.127.191.180"}

@pytest.mark.asyncio
async def test_downloader_middleware_stop(httpbin):
    dl = Downloader()

    class EndlessReqMiddleware(Middleware):
        async def request(self, req: Request, session: Session, dl: "Downloader", **meta):
            return req

    with pytest.raises(MwareRedirectLimit):
        resp = await dl.send(Request(httpbin + '/html'),mwares={0: EndlessReqMiddleware()})

    class EndlessRespMiddleware(Middleware):
        async def response(self, resp: Response, req: Request, session: Session, dl: "Downloader", **meta):
            return req

    with pytest.raises(MwareRedirectLimit):
        resp = await dl.send(Request(httpbin + '/html'),mwares={0: EndlessRespMiddleware()})


@pytest.mark.asyncio
async def test_downloader_pickling(httpbin):
    """pickling shouldn't work with active sessions"""
    dl = Downloader()
    assert pickle.dumps(dl)
    await dl.send(Request(httpbin + '/html'))
    with pytest.raises(TypeError):
        assert pickle.dumps(dl)
