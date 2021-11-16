from requestr.middlewares import Middleware
from requestr import Request, Session
import random


class RandomUserAgent(Middleware):
    def __init__(self, *user_agents) -> None:
        self.user_agents = user_agents

    async def request(self, req: Request, session: Session, dl: "Downloader", **meta):
        if not req.headers.get("User-Agent"):
            req.headers["User-Agent"] = random.choice(self.user_agents)
