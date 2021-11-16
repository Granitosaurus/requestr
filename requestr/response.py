from typing import TYPE_CHECKING, Dict, List, Optional
from aiohttp import ClientResponse, hdrs
from aiohttp.helpers import reify
from yarl import URL
import re
import json
import gzip
from parsel import Selector  # TODO make optional

if TYPE_CHECKING:
    from requestr.request import Request

json_re = re.compile(r"^application/(?:[\w.+-]+?\+)?json")


class Response:
    def __init__(
        self,
        url: URL,
        status: int,
        *,
        content: bytes = b"",
        method: str = "GET",
        headers: Dict = None,
        encoding: str = "utf-8",
        request: Optional["Request"] = None,
        meta: Dict = None,
    ) -> None:
        self.status = status
        self.encoding = encoding
        self._content = content
        self.method = method
        self.url = url
        self.headers = headers or {}
        self.request = request
        self.meta = meta or {}
        self._cache = {}
        self.history: List["Response"] = []

    @reify
    def content(self):
        return self._content

    @reify
    def text(self):
        return self.content.decode(self.encoding)

    @reify
    def tree(self):
        return Selector(text=self.text, base_url=str(self.url))

    @reify
    def json(
        self,
        *,
        content_type: Optional[str] = "application/json",
    ) -> Dict:
        """Read and decodes JSON response."""
        if content_type:
            if not json_re.search(self.headers.get(hdrs.CONTENT_TYPE, "").lower()):
                raise ValueError(
                    f"Attempt to decode JSON with unexpected mimetype",
                )
        return json.loads(self.text)

    @classmethod
    async def from_aiohttp(cls, response: ClientResponse, decompress=True):
        content = await response.read()
        encoding = response.get_encoding()
        headers = response.headers
        if decompress and headers.get("Content-Type") == "application/x-gzip":
            content = gzip.decompress(content)

        return cls(
            url=response.url,
            status=response.status,
            content=content,
            method=response.method,
            headers=headers,
            encoding=encoding,
            request=None,  # TODO
        )

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self.status} {self.url})"