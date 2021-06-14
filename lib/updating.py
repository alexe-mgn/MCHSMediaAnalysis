"""
Utilities for processing site data.
"""
from typing import *
import asyncio

import aiohttp
import sqlalchemy.orm
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy import create_engine

from .fetching import MCHSFetcher
from .parsing import MCHSPageParser, MCHSNewsParser
from .db import *

__all__ = ["MCHSUpdater"]


class MCHSUpdater(MCHSFetcher):
    """
    Class that manages fetching, parsing, updating and processing news.
    """

    def __init__(self,
                 db_url: URL,
                 loop: asyncio.AbstractEventLoop = None,
                 session: aiohttp.ClientSession = None,
                 max_page_requests: int = None, max_news_requests: int = None,
                 max_requests: int = None):
        super().__init__(loop, session, max_page_requests, max_news_requests, max_requests)
        self.engine: Engine = create_engine(db_url)
        self.Session = scoped_session(sessionmaker(self.engine))

    class PageUpdateTask(MCHSFetcher.PageRequestTask):
        manager: "MCHSUpdater"

        def __init__(self, manager: "MCHSFetcher", page: int, *,
                     method: str = "get", retry: int = 0,
                     overwrite: bool = False,
                     name: str = None, **kwargs) -> None:
            """
            :param overwrite: fetch and overwrite news even if they are already present in DB.
            """
            super().__init__(manager, page,
                             method=method, retry=retry,
                             name=name if name is not None else f"MCHS page {page} update", **kwargs)
            self.overwrite = overwrite
            self.news = []

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            if not resp.ok:
                raise RuntimeError(f"Page {self.page} request returned with status code {resp.status}.")
            # Await response HTML and parse
            self.news = await self._retreive_news(resp)
            await self._update_news()

        async def _retreive_news(self, resp: aiohttp.ClientResponse) -> List[Dict[str, Any]]:
            if not (news := MCHSPageParser(await resp.text(encoding='utf8')).parse()):
                raise RuntimeError(f"Page {self.page} request returned without news payload.")
            return news

        async def _update_news(self):
            for i in self.news:
                news_id: int = i['id']
                # Check news update needed
                with self.manager.Session() as session:
                    session: sqlalchemy.orm.Session
                    existing = session.query(ExistingNews).filter_by(id=news_id).one_or_none() is not None
                    if not existing and session.query(News).filter_by(id=news_id).one_or_none() is None:
                        session.add(ExistingNews(id=news_id))
                        existing = True
                        session.commit()
                if existing or self.overwrite:
                    # Update news task
                    self.manager.update_news(news_id, url=i.get("link", None), retry=self.retry)

    class PageUpdateWhileTask(PageUpdateTask):

        def __init__(self, manager: "MCHSFetcher", page: int, test: Callable[[Dict[str, Any]], bool] = None, *,
                     method: str = "get", retry: int = 0,
                     overwrite: bool = False,
                     name: str = None, **kwargs) -> None:
            super().__init__(manager, page,
                             method=method, retry=retry,
                             overwrite=overwrite,
                             name=name if name else f"MCHS page {page} update while", **kwargs)
            self.test = test
            self.kwargs = kwargs

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            await super().response(resp, **kwargs)
            if self.news:
                self.manager.register_task(self.__class__(
                    self.manager, self.page + 1, self.test,
                    method=self.method, retry=self.retry, overwrite=self.overwrite, **self.kwargs
                ))

        async def _retreive_news(self, resp: aiohttp.ClientResponse) -> List[Dict[str, Any]]:
            return list(filter(self.test, await super()._retreive_news(resp)))

    class NewsUpdateTask(MCHSFetcher.NewsRequestTask):
        manager: "MCHSUpdater"

        def __init__(self, manager: "MCHSFetcher", news_id: int, *,
                     url: str = None, method: str = "get", retry: int = 0,
                     name: str = None, **kwargs) -> None:
            super().__init__(manager, news_id,
                             url=url, method=method, retry=retry,
                             name=name if name is not None else f"MCHS news id {news_id} update", **kwargs)
            self.news = {}

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            if not resp.ok:
                raise RuntimeError(f"News id {self.news_id} request returned with status code {resp.status}.")
            self.news = MCHSNewsParser(await resp.text(encoding='utf8')).parse()
            await self._write_news()

        async def _write_news(self):
            """
            Write data dict as news to database.
            """
            data = self.news
            with self.manager.Session() as session, session.begin():
                session: sqlalchemy.orm.Session
                news = session.merge(News(
                    **{k: v for k, v in data.items() if k in {"id", "title", "date", "text", "image"}}))
                if "categories" in data.keys():
                    news.categories_assoc.clear()
                if "tags" in data.keys():
                    news.tags_assoc.clear()
                session.flush((news,))
                # Filling categories and tags
                categories = [session.merge(Category(**category)) for category in data.get("categories", ())]
                tags = [session.merge(Tag(**tag)) for tag in data.get("tags", ())]
                session.add_all(
                    NewsCategories(news=news, category=category, priority=n) for n, category in enumerate(categories))
                session.add_all(
                    NewsTags(news=news, tag=tag, priority=n) for n, tag in enumerate(tags))
                session.query(ExistingNews).filter_by(id=news.id).delete()

    def update_page(self, page: int, overwrite: bool = False, **kwargs):
        """
        :param page: page index.
        :param overwrite: fetch and overwrite news even if they are already present in DB.
        """
        self.register_task(self.PageUpdateTask(self, page, overwrite=overwrite, **kwargs))

    def update_news(self, news_id: int, **kwargs):
        self.register_task(self.NewsUpdateTask(self, news_id, **kwargs))

    def update_while(self, test: Callable[[Dict[str, Any]], bool], overwrite: bool = False, **kwargs):
        self.register_task(self.PageUpdateWhileTask(self, 1, test, overwrite=overwrite, **kwargs))
