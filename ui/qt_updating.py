from typing import *
import datetime

import asyncio

import aiohttp

from sqlalchemy.engine import URL

from PyQt5.QtCore import QObject, pyqtSignal as Signal, QRunnable

from lib import MCHSUpdater

if TYPE_CHECKING:
    from .updater import Updater, UPDATE_RANGE


class QtMCHSUpdater(MCHSUpdater, QObject):

    def __init__(self, db_url: URL, loop: asyncio.AbstractEventLoop = None, session: aiohttp.ClientSession = None,
                 max_page_requests: int = None, max_news_requests: int = None, max_requests: int = None):
        QObject.__init__(self)
        MCHSUpdater.__init__(self, db_url, loop, session, max_page_requests, max_news_requests, max_requests)

    def task_started(self, task: MCHSUpdater.AsyncTask, /):
        if isinstance(task, self.PageUpdateTask):
            self.page_requested.emit(task.page)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_requested.emit(task.news_id)

    page_requested = Signal(int)
    news_requested = Signal(int)

    def task_failed(self, task: MCHSUpdater.AsyncTask, /,
                    etype: Type[BaseException] = None, evalue: BaseException = None, etraceback=None):
        self.task_raised.emit(etype, evalue, etraceback)
        if isinstance(task, self.PageUpdateTask):
            self.page_failed.emit(task.page, etype, evalue, etraceback)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_failed.emit(task.news_id, etype, evalue, etraceback)

    task_raised = Signal([object, object, object])
    page_failed = Signal([int, object, object, object])
    news_failed = Signal([int, object, object, object])

    def task_successful(self, task: MCHSUpdater.AsyncTask, /):
        if isinstance(task, self.PageUpdateTask):
            self.page_successful.emit(task.page, task.news)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_successful.emit(task.news_id, task.news)

    page_successful = Signal([int, list])
    news_successful = Signal([int, dict])

    def task_finished(self, task: MCHSUpdater.AsyncTask, /):
        if isinstance(task, self.PageUpdateTask):
            self.page_finished.emit(task.page)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_finished.emit(task.news_id)

    page_finished = Signal(int)
    news_finished = Signal(int)

    def run_all(self):
        self.update_started.emit()
        super().run_all()

    update_started = Signal()

    def all_finished(self):
        self.update_finished.emit()

    update_finished = Signal()


class MCHSUpdate(QRunnable):

    def __init__(self, updater: "Updater", url: URL,
                 lower: Optional[datetime.datetime], upper: Optional[datetime.datetime], *,
                 max_page_requests: int = None,
                 max_news_requests: int = None, max_requests: int = None,
                 **kwargs):
        super().__init__()
        self._updater = updater
        self._url = url
        self._range: "UPDATE_RANGE" = (lower, upper)
        self._r_limits = (max_page_requests, max_news_requests, max_requests)
        self._kwargs = kwargs

        self._news_updater: Optional[QtMCHSUpdater] = None

    @property
    def url(self) -> URL:
        return self._url

    @property
    def range(self) -> "UPDATE_RANGE":
        return self._range

    def run(self):
        p, n, r = self._r_limits
        nu = QtMCHSUpdater(self._url, max_page_requests=p, max_news_requests=n, max_requests=r)
        if (uw := self._updater.update_window) is not None:
            nu.update_started.connect(uw.update_started)
            nu.page_requested.connect(uw.page_requested)
            nu.news_requested.connect(uw.news_requested)
            nu.task_raised.connect(uw.task_raised)
            nu.news_failed.connect(uw.news_failed)
            nu.news_successful.connect(uw.news_successful)
            nu.update_finished.connect(uw.update_finished)
        nu.update_finished.connect(self._updater._update_finished)
        nu.update_range("date", *self._range, **self._kwargs)
        self._news_updater = nu
        nu.run_all()
        self._news_updater = None

    def stop(self):
        self._news_updater.stop()
