from typing import List, Any
from httpx import Request


class RequestFailed(Exception):
    """
    Exception raised when request is unretrievable
    in acceptable format. eg. retry middleware exceeded retries
    """

    def __init__(self, req: Request, reason, *args, **kwargs):
        self.req = req
        self.reason = reason
        self.args = args
        self.kwargs = kwargs


class RequestDropped(Exception):
    """
    Exception raised when request is should not be sent out
    retry middleware exceeded retries
    """

    def __init__(self, req: Request, reason, *args, **kwargs):
        self.req = req
        self.reason = reason
        self.args = args
        self.kwargs = kwargs

class MwareRedirectLimit(Exception):
    def __init__(self, reason:str, history: List[Request], *args, **kwargs):
        self.reason = reason
        self.history = history
        self.args = args
        self.kwargs = kwargs

class UnsupportedMwareReturn(Exception):
    def __init__(self, reason:str, got: Any, *args, **kwargs):
        self.reason = reason
        self.got = got
        super().__init__(*args)