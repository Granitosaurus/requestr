# Requestr

⚠ This is WIP experiment ⚠

requestr is web-scraping focused http client based on aiohttp. Goals of requestr:

- Concurrency and multi-session support
- Proxy support
- Default http response/exception handlers
- Easy extension of custom handling via post/pre middlewares

# Example

Single request
```python
from requestr import Download, Request

async with Downloader() as dl:
    resp = await dl.send(Request("http://httpbin.org/html"))
    print(resp.text)
```

Concurrent requests:
```python
from requestr import Download, Request
import asyncio

async with Downloader() as dl:
    # 10 different pages concurrently
    for resp in asyncio.as_completed([dl.send(f"http://httpbin.org/links/10/{i}" for i range(10))]):
        print(await resp)
```

Multi session requests:
```python
from requestr import Download, Request

async with Downloader() as dl:
    resp = await dl.send(Request("http://httpbin.org/cookies/set/my_cookie/value", slot="foo"))
    resp = await dl.send(Request("http://httpbin.org/cookies", slot="foo"))
    print(resp.text)  # <= {"cookies": {"my_cookie": "value"}}
    resp = await dl.send(Request("http://httpbin.org/cookies", slot="bar"))
    print(resp.text)  # <= {"cookies": {}}  
```
