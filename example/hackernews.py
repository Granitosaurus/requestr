"""
Web Scraper using Downloader to scrape ycombinator.com news (aka Hacker News)

Scrapes first page of comments on every topic in page 1
"""
from asyncio import as_completed
from time import time
from typing import List

from yarl import URL

from requestr import Downloader, Request


class HNCommentsScraper:
    def __init__(self):
        self.dl = Downloader(limit=1)
        self.stats = self.dl.stats

    async def __aenter__(self):
        """starts some stats on"""
        self.stats["start"] = time()
        await self.dl.open()
        return self

    async def __aexit__(self, *args, **kwargs):
        """calculate some end scrape stats and close connections"""
        self.stats["end"] = time()
        self.stats["elapsed"] = self.stats["end"] - self.stats["start"]
        await self.dl.close()

    async def scrape_comments(self, url: URL) -> List[str]:
        resp = await self.dl.send(Request(url))
        return resp.tree.css(".commtext::text").extract()

    async def scrape_page(self, page: int = 1) -> List[URL]:
        front_page = await self.dl.send(Request(f"https://news.ycombinator.com/news?p={page}"))
        urls = []
        for url in front_page.tree.css(".subtext>a:last-child::attr(href)").extract():
            if "item" not in url:
                continue
            urls.append(front_page.url.join(URL(url)))
        return urls


async def scrape():
    comments = []
    async with HNCommentsScraper() as scraper:
        page_urls = await scraper.scrape_page(page=1)
        for data in as_completed([scraper.scrape_comments(url) for url in page_urls]):
            comments.append(await data)

    print(f"found {len(comments)} comments in 1 page of hacker news")
    print(f"stats: {dict(scraper.stats)}")
    return comments


if __name__ == "__main__":
    import asyncio
    import sys
    from loguru import logger

    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss.S}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>: <level>{message}</level>",
    )
    asyncio.run(scrape())
