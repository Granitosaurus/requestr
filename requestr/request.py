from typing import Union, Dict, Optional, Any, Mapping
from types import SimpleNamespace
from dataclasses import dataclass, field
from ssl import SSLContext
from typing import (
    Any,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Union,
)


from aiohttp.typedefs import LooseCookies, LooseHeaders, StrOrURL
from aiohttp.helpers import BasicAuth
from aiohttp.typedefs import LooseCookies, LooseHeaders
from aiohttp.helpers import sentinel
from aiohttp.client import ClientTimeout
from aiohttp.client_reqrep import Fingerprint
from yarl import URL



class Request:
    def __init__(
        self,
        url: StrOrURL,
        method: str = "GET",
        params: Optional[Mapping[str, str]] = None,
        data: Any = None,
        json: Any = None,
        cookies: Optional[LooseCookies] = None,
        headers: Optional[LooseHeaders] = None,
        skip_auto_headers: Optional[Iterable[str]] = None,
        auth: Optional[BasicAuth] = None,
        allow_redirects: bool = True,
        max_redirects: int = 10,
        compress: Optional[str] = None,
        chunked: Optional[bool] = None,
        expect100: bool = False,
        raise_for_status: Optional[bool] = None,
        read_until_eof: bool = True,
        proxy: Optional[StrOrURL] = None,
        proxy_auth: Optional[BasicAuth] = None,
        timeout: Union[ClientTimeout, object] = sentinel,
        verify_ssl: Optional[bool] = None,
        fingerprint: Optional[bytes] = None,
        ssl_context: Optional[SSLContext] = None,
        ssl: Optional[Union[SSLContext, bool, Fingerprint]] = None,
        proxy_headers: Optional[LooseHeaders] = None,
        trace_request_ctx: Optional[SimpleNamespace] = None,
        read_bufsize: Optional[int] = None,
        # extended,
        meta: Dict = None,
        slot: str = "",
        ):
            self.url = URL(url)
            self.slot = slot or self.url.host
            self.meta = meta or {}
            self.method = method
            self.params = params
            self.data = data
            self.json = json
            self.cookies = cookies
            self.headers = headers or {}
            self.skip_auto_headers = skip_auto_headers
            self.auth = auth
            self.allow_redirects = allow_redirects
            self.max_redicrects = max_redirects
            self.compress = compress
            self.chuncked = chunked
            self.expect100 = expect100
            self.raise_for_status = raise_for_status
            self.read_unti_eof = read_until_eof
            self.proxy = proxy
            self.proxy_auth = proxy_auth
            self.timeout = timeout
            self.verify_ssl = verify_ssl
            self.fingerprint = fingerprint
            self.ssl_context = ssl_context
            self.ssl = ssl
            self.proxy_headers = proxy_headers
            self.trace_request_ctx = trace_request_ctx
            self.read_buffsize = read_bufsize

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.method} {self.url})"