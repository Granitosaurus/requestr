from collections import defaultdict
from copy import deepcopy
from time import time
from typing import Callable, Dict, List, Optional, Type

from loguru import logger as log
from aiohttp import TCPConnector
from aiolimiter import AsyncLimiter

from requestr.defaults import DEFAULT_LIMIT
from requestr.exceptions import MwareRedirectLimit, UnsupportedMwareReturn
from requestr.middlewares import Middleware, RetryExceptions, RetryStatuses, RandomUserAgent
from requestr.request import Request
from requestr.response import Response
from requestr.session import Session
from requestr.throttler import Throttler

DEFAULT_MWARES = {
    # downloader
    100: RandomUserAgent(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36."
    ),
    900: RetryStatuses(),
    1000: RetryExceptions(),
    # web
}
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36.",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
}
DEFAULT_SESSION_KWARGS = {
    "headers": DEFAULT_HEADERS,
}


class Downloader:
    def __init__(
        self,
        mwares: Optional[Dict[int, Middleware]] = DEFAULT_MWARES,
        session_cls: Callable = Session,
        session_kwargs: Dict = None,
        limit: int = 120,
    ):
        self.sessions = {}
        self.session_kwargs = session_kwargs or DEFAULT_SESSION_KWARGS
        self.stats = defaultdict(float)
        self.mwares = mwares
        self.mware_req_limit = 10
        self.session_cls = session_cls
        self.limit = limit

    async def new_session(
        self,
        key: str,
        session_cls: Type[Session] = None,
        limit=None,
        session_defaults=True,
        **session_kwargs,
    ) -> Session:
        """
        create new session

        Parameters
        ----------
        key : str
            [description]
        session_cls : Type[Session], optional
            [description], by default None
        limit : int, optional
            [description], by default 120
        session_defaults : bool, optional
            [description], by default True

        Returns
        -------
        Session
            [description]
        """
        if not session_cls:
            session_cls = self.session_cls
        if not limit:
            limit = self.limit
        if session_defaults:
            session_kwargs = {**self.session_kwargs, **session_kwargs}
        key = str(key)

        log.info(f"starting session {key} based on {session_cls}")
        self.stats["session/new"] += 1
        try:
            await self.sessions[key].close()
            log.debug(f"closed existing session on {key}")
        except KeyError:
            pass

        new_session = session_cls(**session_kwargs)
        new_session.limiter = AsyncLimiter(limit, 1)
        self.sessions[key] = new_session
        return self.sessions[key]

    async def _send(self, req: Request, session: Session):
        async with session.limiter:
            resp = await session._request(
                method=req.method,
                str_or_url=req.url,
                params=req.params,
                data=req.data,
                json=req.json,
                cookies=req.cookies,
                headers=req.headers,
                skip_auto_headers=req.skip_auto_headers,
                auth=req.auth,
                allow_redirects=req.allow_redirects,
                max_redirects=req.max_redicrects,
                compress=req.compress,
                chunked=req.chuncked,
                expect100=req.expect100,
                raise_for_status=req.raise_for_status,
                read_until_eof=req.read_unti_eof,
                proxy=req.proxy,
                proxy_auth=req.proxy_auth,
                timeout=req.timeout,
                verify_ssl=req.verify_ssl,
                fingerprint=req.fingerprint,
                ssl_context=req.ssl_context,
                ssl=req.ssl,
                proxy_headers=req.proxy_headers,
                trace_request_ctx=req.trace_request_ctx,
                read_bufsize=req.read_buffsize,
            )
        self.stats["req/sent"] += 1
        resp = await Response.from_aiohttp(resp)
        resp.request = req
        return resp

    async def send(
        self,
        req: Request,
        mwares: Dict[int, Middleware] = None,
    ) -> Response:
        if mwares is None:
            mwares = self.mwares

        log.debug(f'{req} on "{req.slot}"')
        self.stats["req/scheduled"] += 1

        _redirect_history = []
        while len(_redirect_history) < self.mware_req_limit:
            if req.slot not in self.sessions:
                session = await self.new_session(req.slot)
            else:
                session = self.sessions[req.slot]

            # request middleware
            req_mid_result = await self.process_req(req, session=session, mwares=mwares)
            if isinstance(req_mid_result, Request):
                log.debug(f"{req} reformed to {req_mid_result} by req middleware")
                _redirect_history.append(req)
                self.stats["reqmid/return/req"] += 1
                req = req_mid_result
                continue
            if isinstance(req_mid_result, Response):
                log.debug(f"{req} redirected to local response {req_mid_result} by req middleware")
                self.stats["reqmid/return/resp"] += 1
                return req_mid_result
            if req_mid_result is not None:
                raise UnsupportedMwareReturn("unhandled request middleware return", req_mid_result)

            # exception middleware
            try:
                resp = await self._send(req, session)
            except Exception as e:
                exc_mid_result = await self.process_resp_exception(e, req=req, session=session, mwares=mwares)
                if isinstance(exc_mid_result, Request):
                    log.debug(f"{req} exception {e} reformed to {exc_mid_result}")
                    self.stats["respmid/exc/req"] += 1
                    _redirect_history.append(req)
                    req = exc_mid_result
                    continue
                if isinstance(exc_mid_result, Response):
                    log.debug(f"{req} exception {e} redirect to local response {exc_mid_result}")
                    self.stats["respmid/exc/resp"] += 1
                if exc_mid_result is not None:
                    raise UnsupportedMwareReturn("unhandled exception middleware return", req_mid_result)
                raise  # unhandled :(

            # response middleware
            resp_mid_result = await self.process_resp(resp, session=session, mwares=mwares)
            if resp_mid_result is None:
                log.debug(f"{req} got {resp.status}")
                resp.request = req
                return resp
            if isinstance(resp_mid_result, Request):
                _redirect_history.append(req)
                log.debug(f"{req} reformed to {resp_mid_result} by response middleware")
                self.stats["respmid/return/req"] += 1
                req = resp_mid_result
                continue
            if isinstance(resp_mid_result, Response):
                log.debug(f"{req} redirected to local response {resp_mid_result} by response middleware")
                self.stats["respmid/return/resp"] += 1
                return resp_mid_result
            if req_mid_result is not None:
                raise UnsupportedMwareReturn("unhandled response middleware return", resp_mid_result)
            return resp
        raise MwareRedirectLimit(f"too many middleware redirects {self.mware_req_limit}", history=_redirect_history)

    async def process_req(self, req: Request, session: Session, mwares: List[Middleware]):
        for mw in sorted(list(mwares)):
            mw = mwares[mw]
            if result := await mw.request(req=req, session=session, dl=self):
                # TODO stats here
                return result

    async def process_resp(self, resp: Response, session: Session, mwares: Dict[int, Middleware]):
        for mw in sorted(list(mwares), reverse=True):
            mw = mwares[mw]
            if result := await mw.response(resp=resp, req=resp.request, session=session, dl=self):
                # TODO stats here
                return result

    async def process_resp_exception(self, exc: Exception, req: Request, session: Session, mwares: List[Middleware]):
        for mw in sorted(list(mwares), reverse=True):
            mw = mwares[mw]
            if result := await mw.response_exception(exc=exc, req=req, session=session, dl=self):
                # TODO stats here
                return result

    async def close(self):
        for key, session in self.sessions.items():
            log.debug(f'closing session "{key}"')
            await session.close()
        self.sessions = {}
        self.stats["close"] = time()
        if self.stats.get("open"):
            self.stats["elapsed"] = self.stats["close"] - self.stats["open"]
        log.info(dict(self.stats))

    async def open(self):
        self.stats["open"] = time()

    async def __aenter__(self):
        """starts some stats on"""
        await self.open()
        self.stats["start"] = time()
        return self

    async def __aexit__(self, *args, **kwargs):
        """calculate some end scrape stats and close connections"""
        self.stats["end"] = time()
        self.stats["elapsed"] = self.stats["end"] - self.stats["start"]
        await self.close()
