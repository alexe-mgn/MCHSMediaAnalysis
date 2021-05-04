"""
Classes for retrieving data from site.
"""
import asyncio
import urllib.parse

import aiohttp

from edge_finder import AbstractEdgeFinder, DividingEdgeFinder
from async_tasks import RequestManager

__all__ = ["MCHSFetcher", "MCHSPageEdgeFinder"]


class MCHSFetcher(RequestManager):
    """
    Class for retrieving mchsmedia data.
    """
    base_url = "http://mchsmedia.ru/"

    # TaskClass = PageRequestTask

    class PageRequestTask(RequestManager.RequestTask):
        manager: "MCHSFetcher"
        url_pattern = "news/{}/"

        def __init__(self, manager: "MCHSFetcher", page: int, *,
                     name: str = None, **kwargs) -> None:
            super().__init__(manager, url=(manager.base_url + self.url_pattern).format(page), method="get",
                             name=name if name is not None else f"MCHS page {page} request", **kwargs)
            self.page = page

    def request_page(self, page: int, **kwargs):
        self.register_task(self.PageRequestTask(self, page, **kwargs))

    class NewsRequestTask(RequestManager.RequestTask):
        """
        Sometimes news tend to appear under /focus/item/{}/ for uncertain time.
        For such cases and more, optional url parameter is provided.
        """
        manager: "MCHSFetcher"
        url_pattern = "news/item/{}/"

        def __init__(self, manager: "MCHSFetcher", news_id: int, url: str = None, *,
                     name: str = None, **kwargs) -> None:
            """
            :param url: Preferred over .url_pattern and also formatted with news_id as argument.
            """
            url = (url if url is not None else self.url_pattern).format(news_id)
            super().__init__(manager,
                             url=urllib.parse.urljoin(manager.base_url, url)
                             if not urllib.parse.urlparse(url).netloc
                             else url,
                             method="get",
                             name=name if name is not None else f"MCHS news id {news_id} request", **kwargs)
            self.news_id = news_id

    def request_news(self, news_id: int, **kwargs):
        self.register_task(self.NewsRequestTask(self, news_id, **kwargs))


class MCHSPageEdgeFinder(MCHSFetcher):
    """
    Class that uses edge finders to find last valid news page.
    """

    # TaskClass = MCHSPageEdgeRequest

    class PageRequestTask(MCHSFetcher.PageRequestTask):
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
