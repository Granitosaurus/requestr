from httpx import Request as HttpxRequest
from httpx._types import QueryParamTypes, HeaderTypes, CookieTypes, RequestContent, RequestData, RequestFiles, RawURL
from httpx._transports.base import SyncByteStream, AsyncByteStream

from requestr.utils import domain_from_url


class _Request(HttpxRequest):
    def __init__(
        self,
        url: typing.Union["URL", str, RawURL],
        method: typing.Union[str, bytes] = "GET",
        *,
        params: QueryParamTypes = None,
        headers: HeaderTypes = None,
        cookies: CookieTypes = None,
        content: RequestContent = None,
        data: RequestData = None,
        files: RequestFiles = None,
        json: typing.Any = None,
        stream: typing.Union[SyncByteStream, AsyncByteStream] = None,
        meta: Dict = None,
        slot: str = None,
    ):
        super().__init__(
            method=method,
            url=url,
            params=params,
            headers=headers,
            cookies=cookies,
            content=content,
            data=data,
            files=files,
            json=json,
            stream=stream,
        )
        self.slot = domain_from_url(self.url) if slot is None else slot
        self.meta = meta or {}

