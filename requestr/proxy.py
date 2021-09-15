from typing import List, Optional
from aiohttp import BasicAuth
from aiohttp.typedefs import LooseHeaders
import random


class ProxyPool:
    
    def __init__(self, pool: List[str], auth: Optional[BasicAuth] = None, headers: Optional[LooseHeaders] = None) -> None:
        self.proxies = pool
        self.auth = auth
        self.headers = headers
        self._pool = []

    @property
    def pool(self):
        if not self._pool:
            self._pool = self.proxies.copy()
            random.shuffle(self._pool)
        return self._pool

    @property 
    def random(self):
        """return random proxy"""
        return self.pool.pop()


