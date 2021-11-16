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


from requestr.middlewares.headers import RandomUserAgent
from requestr.middlewares.proxy import RotatingProxyPool
from requestr.middlewares.retry import RetryStatuses, RetryExceptions
