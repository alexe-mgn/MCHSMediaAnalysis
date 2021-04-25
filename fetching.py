"""
Classes for retrieving data from site.
"""

import asyncio

import aiohttp

from async_tasks import RequestManager
from edge_finder import AbstractEdgeFinder, DividingEdgeFinder

__all__ = ["MCHSPageFetcher", "MCHSNewsFetcher", "MCHSPageEdgeFinder"]


class MCHSPageFetcher(RequestManager):
    """
    Class for retrieving page with news.
    """

    # TaskClass = PageRequestTask

    class PageRequestTask(RequestManager.RequestTask):
        manager: "MCHSPageFetcher"
        url_pattern = "http://www.mchsmedia.ru/news/%d/"

        def __init__(self, manager: "MCHSPageFetcher", page: int, *,
                     name: str = None, **kwargs) -> None:
            super().__init__(manager, url=self.url_pattern % page, method="get",
                             name=name if name is not None else f"MCHS page {page} request", **kwargs)
            self.page = page

    def request_page(self, page: int):
        self.register_task(self.PageRequestTask(self, page))


class MCHSPageEdgeFinder(MCHSPageFetcher):
    """
    Class that uses edge finders to find last valid news page.
    """

    # TaskClass = MCHSPageEdgeRequest

    class PageRequestTask(MCHSPageFetcher.PageRequestTask):
        manager: "MCHSPageEdgeFinder"

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            await super().response(resp, **kwargs)
            await self.manager.validate(self.page, valid=resp.ok, resp=resp)

    def __init__(self, loop: asyncio.AbstractEventLoop = None, session: aiohttp.ClientSession = None,
                 edge_finder: AbstractEdgeFinder = None):
        super().__init__(loop, session)
        self.edge_finder = edge_finder if edge_finder is not None else DividingEdgeFinder(left=1, step=10000, coef=2)

    def test(self):
        requested = {i.page for i in self._tasks}
        for i in self.edge_finder.get_probes():
            if i not in requested:
                self.request_page(i)

    async def validate(self, page: int, valid: bool = False, resp: aiohttp.ClientResponse = None):
        self.edge_finder.validate(page, valid)
        left, right = self.edge_finder.edge
        for i in self._tasks:
            if isinstance(i, self.PageRequestTask) and not left <= i.page <= right:
                i.cancel()
        if not self.edge_finder.found:
            self.test()


class MCHSNewsFetcher(RequestManager):
    """
    Class for retrieving news item.
    """

    # TaskClass = NewsRequestTask

    class NewsRequestTask(RequestManager.RequestTask):
        url_pattern = "http://www.mchsmedia.ru/news/item/%d/"

        def __init__(self, manager: "MCHSNewsFetcher", news_id: int, *,
                     name: str = None, **kwargs) -> None:
            super().__init__(manager, self.url_pattern % news_id, method="get",
                             name=name if name is not None else f"MCHS news id {news_id} request", **kwargs)
            self.news_id = news_id

    def request_news(self, news_id: int):
        self.register_task(self.NewsRequestTask(self, news_id))
