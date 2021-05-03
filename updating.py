"""
Utilities for processing site data.
"""
from typing import *
import asyncio

import aiohttp
import sqlalchemy.orm
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker, scoped_session

from fetching import MCHSFetcher
from parsing import MCHSPageParser, MCHSNewsParser
from db import *

__all__ = ["MCHSUpdater"]


class MCHSUpdater(MCHSFetcher):
    """
    Class that manages fetching, parsing, updating and processing news.
    """

    def __init__(self, engine: Engine, loop: asyncio.AbstractEventLoop = None, session: aiohttp.ClientSession = None):
        super().__init__(loop, session)
        self.engine = engine
        self.Session = scoped_session(sessionmaker(engine))

    class PageUpdateTask(MCHSFetcher.PageRequestTask):
        manager: "MCHSUpdater"

        def __init__(self, manager: "MCHSFetcher", page: int, overwrite: bool = False, *,
                     name: str = None, **kwargs) -> None:
            """
            :param overwrite: fetch and overwrite news even if they are already present in DB.
            """
            super().__init__(manager, page,
                             name=name if name is not None else f"MCHS page {page} update", **kwargs)
            self.overwrite = overwrite

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            if not resp.ok:
                raise RuntimeError(f"Page {self.page} request returned with status code {resp.status}.")
            else:
                # Await response HTML and parse
                news = MCHSPageParser(await resp.text(encoding='utf8')).parse()
                for i in news:
                    news_id = i['id']
                    # Check news update needed
                    if not self.overwrite:
                        with self.manager.Session() as session:
                            upd = session.query(News).filter_by(id=news_id).one_or_none() is None \
                                  or session.query(ExistingNews).filter_by(id=news_id).one_or_none() is not None
                    else:
                        upd = True
                    if upd:
                        # Update news task
                        self.manager.update_news(news_id)

    class NewsUpdateTask(MCHSFetcher.NewsRequestTask):
        manager: "MCHSUpdater"

        def __init__(self, manager: "MCHSFetcher", news_id: int, *, name: str = None, **kwargs) -> None:
            super().__init__(manager, news_id,
                             name=name if name is not None else f"MCHS news id {news_id} update", **kwargs)

        async def response(self, resp: aiohttp.ClientResponse, **kwargs):
            if not resp.ok:
                raise RuntimeError(f"News id {self.news_id} request returned with status code {resp.status}.")
            await self.write_news(MCHSNewsParser(await resp.text(encoding='utf8')).parse())

        async def write_news(self, data: Dict[str, Any]):
            """
            Write data dict as news to database.
            """
            with self.manager.Session() as session, session.begin():
                session: sqlalchemy.orm.Session
                news = session.merge(News(
                    **{k: v for k, v in data.items() if k in {"id", "title", "date", "text", "image"}}))
                # news = session.merge(News(id=data['id'],
                #                           title=data.get('title', None),
                #                           date=data.get('date', None),
                #                           text=data.get('text', None),
                #                           image=data.get('image', None)))
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

    def update_page(self, page: int, overwrite: bool = False):
        """
        :param page: page index.
        :param overwrite: fetch and overwrite news even if they are already present in DB.
        """
        self.register_task(self.PageUpdateTask(self, page, overwrite=overwrite))

    def update_news(self, news_id: int):
        self.register_task(self.NewsUpdateTask(self, news_id))
