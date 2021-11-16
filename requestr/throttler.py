import asyncio
from typing import Deque
from time import time


class Throttler:
    def __init__(self, rate_limit, period=1.0, retry_interval=0.01):
        self.rate_limit = rate_limit
        self.period = period
        self.retry_interval = retry_interval

        self._task_logs = Deque()

    def flush(self):
        now = time()
        while self._task_logs:
            if now - self._task_logs[0] > self.period:
                self._task_logs.popleft()
            else:
                break

    async def acquire(self):
        while True:
            self.flush()
            if len(self._task_logs) < self.rate_limit:
                break
            await asyncio.sleep(self.retry_interval)

        self._task_logs.append(time())

    async def __aenter__(self):
        await self.acquire()


    async def __aexit__(self, exc_type, exc, tb):
        pass
