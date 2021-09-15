from httpx import AsyncClient
import logging
import asyncio
from typing import TYPE_CHECKING, Union
from httpx._client import UseClientDefault, USE_CLIENT_DEFAULT

if TYPE_CHECKING:
    from requestr.request import Request
    from requestr.response import Response
    from httpx._types import (
        AuthTypes,
        TimeoutTypes,
    )

from aiohttp import ClientSession as Session

class _Session:
    """http session manager"""

    def __init__(self, *args, **kwargs):
        self.client = AsyncClient(*args, **kwargs)
        self.ready = False
        self.log = logging.getLogger(type(self).__name__)
        self.proxy = None

    async def send(
        self,
        request: "Request",
        *,
        stream: bool = False,
        auth: Union["AuthTypes", UseClientDefault] = USE_CLIENT_DEFAULT,
        allow_redirects: Union[bool, UseClientDefault] = USE_CLIENT_DEFAULT,
        timeout: Union["TimeoutTypes", UseClientDefault] = USE_CLIENT_DEFAULT,
    ) -> "Response":
        """"""
        while not self.ready:  # TODO add timeout here
            await asyncio.sleep(0.1)
        return await self.client.send(request=request, stream=stream, auth=auth, allow_redirects=allow_redirects, timeout=timeout)

    async def switch_proxy(self, proxy):
        self.log.debug(f"switching proxy to: {proxy}")
        self.ready = False
        await self.client.__aexit__()
        self.client.cookies
        self.client.headers
        self.client.timeout
        self.client.auth
        self.client = AsyncClient()  # TODO carry over args/kwargs
        self.proxy = proxy
        await self.client.__aenter__()
        self.ready = True

    async def __aenter__(self):
        await self.client.__aenter__()
        self.ready = True

    async def __aexit__(self):
        await self.client.__aexit__()
        self.ready = False
