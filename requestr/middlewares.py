from requestr.exceptions import RequestFailed, RequestDropped
from requestr.session import Session
from aiohttp import BasicAuth
from aiohttp.client_exceptions import ClientResponseError, ClientConnectionError
from typing import TYPE_CHECKING, Callable, List, Union, Iterator, Tuple
from requestr import Request, Response, request
from requestr.proxy import ProxyPool
from collections import Counter, defaultdict
import random
import asyncio
import logging

if TYPE_CHECKING:
    from requestr.downloader import Downloader

Number = Union[int, float]


class Middleware:
    def __init__(self) -> None:
        self.log = logging.getLogger(type(self).__name__)

    async def request(self, req: Request, session: Session, dl: "Downloader", **meta):
        """
        process request:
        - return Request for new request
        - return Response to stop flow
        - raise RequestDropped
        """
        return

    async def response(self, resp: Response, req: Request, session: Session, dl: "Downloader", **meta):
        """
        process response:
        - return Request for new request
        - return Response to stop flow
        - raise RequestFailed
        """
        return

    async def response_exception(self, exc: Exception, req: Request, session: Session, dl: "Downloader", **meta):
        """
        process response exception:
        - return Request for new request
        - return Response to stop flow
        - raise any exception
        - raise RequestFailed

        if nothing is returned exception will continue to other middlewares
        """
        return


class RetryMW(Middleware):
    _default_sleep = 0, 1, 3, 6, 10, 16, 32, 64, 128

    def __init__(self, times=2, sleep: Union[Number, Tuple[Number]] = None):
        super().__init__()
        self.sleep = sleep or self._default_sleep
        self.times = times

    async def request(self, req: Request, session: Session, dl: "Downloader", **meta):
        # set retry meta to all new requests
        if "max_retries" not in req.meta:
            req.meta["max_retries"] = self.times
        if "retries" not in req.meta:
            req.meta["retries"] = 0

    def _amount_to_sleep(self, req: Request):
        if isinstance(self.sleep, (int, float)):
            return self.sleep
        else:
            return self.sleep[req.meta["retries"]]
        
    async def _retry(self, req: Request, session: Session, dl: "Downloader", **meta):
        retries, max_retries = req.meta["retries"], req.meta["max_retries"]
        if retries >= max_retries:
            raise RequestFailed(req=req, reason=f"retries exceeded after {retries} retries")
        req.meta["retries"] += 1
        dl.stats["req/retry"] += 1

        amount_to_sleep = self._amount_to_sleep(req)
        dl.stats["sleep/elapsed"] += amount_to_sleep

        self.log.debug(f"retrying {req.url} ({retries}/{max_retries} in {amount_to_sleep} seconds) by {type(self)} mware")
        await asyncio.sleep(amount_to_sleep)
        return req
    

 

class RetryExceptions(RetryMW):
    """middleware to retry specific response exceptions"""
    default_exceptions = (ClientResponseError, ClientConnectionError)


    def __init__(self, *exceptions: Callable, times=2, sleep: Union[Number, Tuple[Number]] = None):
        super().__init__(times=times, sleep=sleep)
        self.exceptions = exceptions or self.default_exceptions
    
    async def response_exception(self, exc: Exception, req: Request, session: Session, dl: "Downloader", **meta):
        if not isinstance(exc, self.exceptions):
            return
        return await self._retry(req=req, session=session, dl=dl, **meta)

    def __add__(self, other):
        exceptions = self.exceptions + other.exceptions
        return type(self)(*exceptions, times=self.times, sleep=self.sleep)



class RetryStatuses(RetryMW):
    """middleware to retry specific response statuses"""
    default_statuses = (500, )

    def __init__(self, *statuses: int, times=2, sleep: Union[Number, Tuple[Number]] = None):
        super().__init__(times=times, sleep=sleep)
        self.statuses = statuses or self.default_statuses
    
    async def response(self, resp: Response, req: Request, session: Session, dl: "Downloader", **meta):
        if resp.status not in self.statuses:
            return
        return await self._retry(req=req, session=session, dl=dl, **meta)

    def __add__(self, other):
        statuses = self.statuses + other.statuses
        return type(self)(*statuses, times=self.times, sleep=self.sleep)


class RotatingProxyPool(Middleware):
    """middleware that sets random proxy from proxy pool for every request"""

    def __init__(self, *proxy_pools: ProxyPool) -> None:
        super().__init__()
        self.proxy_pools = proxy_pools

    async def request(self, req: Request, session: Session, dl: "Downloader", **meta):
        if req.proxy:
            return
        pool = random.choice(self.proxy_pools)
        req.proxy = pool.random
        req.proxy_auth = pool.auth
        req.proxy_headers = pool.headers

