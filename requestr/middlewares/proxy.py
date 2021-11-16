import random
from typing import TYPE_CHECKING
from requestr import session
from requestr.middlewares import Middleware
from requestr.proxy import ProxyPool
from requestr.request import Request
from requestr.response import Response
from requestr.session import Session

if TYPE_CHECKING:
    from requestr.downloader import Downloader


class RotatingProxyPool(Middleware):
    """middleware that sets random proxy from proxy pool for every request"""

    def __init__(self, *proxy_pools: ProxyPool) -> None:
        super().__init__()
        self.proxy_pools = proxy_pools

    async def request(self, req: Request, session: session, dl: "Downloader", **meta):
        if req.proxy:
            return
        pool = random.choice(self.proxy_pools)
        req.proxy = pool.random
        req.proxy_auth = pool.auth
        req.proxy_headers = pool.headers
