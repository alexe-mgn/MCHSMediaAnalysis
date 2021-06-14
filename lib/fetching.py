"""
Classes for retrieving data from site.
"""
import time
import asyncio
import urllib.parse

import aiohttp

from .async_tasks import RequestManager

__all__ = ["MCHSFetcher"]


class MCHSFetcher(RequestManager):
    """
    Class for retrieving mchsmedia data.
    """
    base_url = "http://mchsmedia.ru/"

    def __init__(self,
                 loop: asyncio.AbstractEventLoop = None,
                 session: aiohttp.ClientSession = None,
                 max_page_requests: int = None, max_news_requests: int = None,
                 max_requests: int = None):
        self.page_semaphore = asyncio.BoundedSemaphore(max_page_requests) if max_page_requests is not None else None
        self.news_semaphore = asyncio.BoundedSemaphore(max_news_requests) if max_news_requests is not None else None
        super().__init__(loop, session, max_requests)

    # TaskClass = PageRequestTask

    class PageRequestTask(RequestManager.RequestTask):
        url_pattern = "news/{}/"
        manager: "MCHSFetcher"

        def __init__(self, manager: "MCHSFetcher", page: int, *,
                     method: str = "get", retry: int = 0,
                     name: str = None, **kwargs) -> None:
            super().__init__(manager, urllib.parse.urljoin(manager.base_url, self.url_pattern.format(page)),
                             method=method, retry=retry,
                             name=name if name is not None else f"MCHS page {page} request", **kwargs)
            self.page = page

        async def _request(self, **kwargs):
            if (ps := self.manager.page_semaphore) is not None:
                await ps.acquire()
            res = await super()._request(**kwargs)
            if ps is not None:
                ps.release()
            return res

    def request_page(self, page: int, **kwargs):
        self.register_task(self.PageRequestTask(self, page, **kwargs))

    class NewsRequestTask(RequestManager.RequestTask):
        """
        Sometimes news tend to appear under /focus/item/{}/ for uncertain time.
        For such cases and more, optional url parameter is provided.
        """
        manager: "MCHSFetcher"
        url_pattern = "news/item/{}/"

        def __init__(self, manager: "MCHSFetcher", news_id: int, *,
                     url: str = None, method: str = "get", retry: int = 0,
                     name: str = None, **kwargs) -> None:
            """
            :param url: Preferred over .url_pattern and also formatted with news_id as argument.
            """
            url = (url if url is not None else self.url_pattern).format(news_id)
            super().__init__(manager,
                             urllib.parse.urljoin(manager.base_url, url)
                             if not urllib.parse.urlparse(url).netloc
                             else url,
                             method=method, retry=retry,
                             name=name if name is not None else f"MCHS news id {news_id} request", **kwargs)
            self.news_id = news_id

        async def _request(self, **kwargs):
            if (ns := self.manager.news_semaphore) is not None:
                await ns.acquire()
            res = await super()._request(**kwargs)
            if ns is not None:
                ns.release()
            return res

    def request_news(self, news_id: int, **kwargs):
        self.register_task(self.NewsRequestTask(self, news_id, **kwargs))
