import logging

from typing import List, Optional, List, Dict
from collections import defaultdict
from requestr import exceptions
from requestr.middlewares import Middleware, RetryStatuses, RetryExceptions
from requestr.defaults import DEFAULT_LIMIT
from requestr.session import Session
from requestr.request import Request
from requestr.response import Response
from requestr.exceptions import MwareRedirectLimit, RequestDropped, UnsupportedMwareReturn

DEFAULT_MWARES = {
    # downloader
    900: RetryStatuses(),
    1000: RetryExceptions()
    # web
}


class Downloader:
    def __init__(self, limit=DEFAULT_LIMIT, mwares: Optional[Dict[int, Middleware]] = DEFAULT_MWARES):
        self.limit = limit
        self.sessions = {}
        self.stats = defaultdict(float)
        self.log = logging.getLogger(type(self).__name__)
        self.mwares = mwares
        self.mware_req_limit = 10

    async def new_session(self, key, cls=Session) -> Session:
        self.stats["session/new"] += 1
        self.log.debug(f"starting session {key}")
        try:
            await self.sessions[key].close()
        except Exception as e:
            pass

        self.sessions[key] = cls()
        return self.sessions[key]
    
    async def _send(self, req: Request, session: Session):
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
    
    def _mdwares_to_list(self):
        pass


    async def send(self, req: Request, mwares: Dict[int, Middleware] = None) -> Response:
        if mwares is None:
            mwares = self.mwares

        self.log.debug(f"using {req.slot} session for {req} request")
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
                self.log.debug(f"request {req} exception reformed to {req_mid_result} by request middleware")
                _redirect_history.append(req)
                self.stats["reqmid/return/req"] += 1
                req = req_mid_result
                continue
            if isinstance(req_mid_result, Response):
                self.log.debug(f"request {req} redirected to local response {req_mid_result} by request middleware")
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
                    self.log.debug(f"request {req} exception reformed to {exc_mid_result}")
                    self.stats["respmid/exc/req"] += 1
                    _redirect_history.append(req)
                    req = exc_mid_result
                    continue
                if isinstance(exc_mid_result, Response):
                    self.log.debug(f"request {req} exception redirect to local response {exc_mid_result}")
                    self.stats["respmid/exc/resp"] += 1
                if exc_mid_result is not None:
                    raise UnsupportedMwareReturn("unhandled exception middleware return", req_mid_result)
                raise  # unhandled :(


            # response middleware
            resp_mid_result = await self.process_resp(resp, session=session, mwares=mwares)
            if resp_mid_result is None:
                resp.request = req
                return resp
            if isinstance(resp_mid_result, Request):
                _redirect_history.append(req)
                self.log.debug(f"request {req} reformed to {resp_mid_result} by response middleware")
                self.stats["respmid/return/req"] += 1
                req = resp_mid_result
                continue
            if isinstance(resp_mid_result, Response):
                self.log.debug(f"request {req} redirected to local response {resp_mid_result} by response middleware")
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
            self.log.debug(f"closing session {key}")
            await session.close()
        self.sessions = {}
