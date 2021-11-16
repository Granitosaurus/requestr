import pytest
import asyncio
from time import time
from requestr.throttler import Throttler
from aiolimiter import AsyncLimiter


@pytest.mark.asyncio
async def test_Throttler():
    throttle = AsyncLimiter(10, 1)

    async def do():
        async with throttle:
            await asyncio.sleep(1)

    _start = time()
    await asyncio.gather(*[do() for i in range(50)])
    elapsed = time() - _start
    # 10 tasks per second (default) should take 5 seconds
    assert int(elapsed) == 5
