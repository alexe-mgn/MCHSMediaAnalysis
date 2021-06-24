from typing import *
import datetime

import threading
import asyncio

import aiohttp
from PyQt5.QtCore import Qt, QObject, QRunnable, QThreadPool, QTimer
from PyQt5.QtCore import pyqtSignal as Signal
from sqlalchemy.engine import URL

import utils

from lib import MCHSUpdater

from . import app_config

from .scheduler import ScheduleFileStore
from .updater_ui import UpdateWindow, TrayIcon
from .main_window import MainWindow

__all__ = ["UPDATE_RECORD", "UPDATE_RANGE", "Updater"]


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


UPDATE_RANGE = Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]
# Update start time, lower date, upper date, schema, user
UPDATE_RECORD = Tuple[datetime.datetime,
                      Optional[datetime.datetime], Optional[datetime.datetime],
                      str, str]


class MCHSUpdate(QRunnable):

    def __init__(self, updater: "Updater", url: URL,
                 lower: Optional[datetime.datetime], upper: Optional[datetime.datetime], *,
                 max_page_requests: int = None,
                 max_news_requests: int = None, max_requests: int = None,
                 **kwargs):
        super().__init__()
        self._updater = updater
        self._url = url
        self._range: UPDATE_RANGE = (lower, upper)
        self._r_limits = (max_page_requests, max_news_requests, max_requests)
        self._kwargs = kwargs

        self._news_updater: Optional[QtMCHSUpdater] = None

    @property
    def url(self) -> URL:
        return self._url

    @property
    def range(self) -> UPDATE_RANGE:
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


class Updater:

    def __init__(self):
        self._urls: Dict[str, URL] = {}
        self._unauthorized: Set[UPDATE_RECORD] = set()
        self._warned: Set[UPDATE_RECORD] = set()

        self.tray_icon = TrayIcon(self)

        self.schedule_store = ScheduleFileStore(utils.PATH.SCHEDULE)
        self.schedule: List[UPDATE_RECORD] = self.schedule_store.refresh()

        self._update_timer = QTimer()
        self._update_timer.setTimerType(Qt.VeryCoarseTimer)
        self._update_timer.setInterval(10 * 1000)
        self._update_timer.timeout.connect(self.check_updates)

        self._refresh_timer = QTimer()
        self._refresh_timer.setTimerType(Qt.VeryCoarseTimer)
        self._refresh_timer.setInterval(5 * 60 * 1000)
        self._refresh_timer.timeout.connect(self.refresh_updates)

        self.update_window: Optional[UpdateWindow] = None
        self.update: Optional[MCHSUpdate] = None
        self.main_window: Optional[MainWindow] = None

        self.tray_icon.show()
        self.check_updates()
        self._update_timer.start()
        self._refresh_timer.start()

    def register_user(self, url: URL):
        self._urls[url.username] = url
        self.check_updates()

    def warn_unauthorized_updates(self, force: bool = True):
        warn = self._unauthorized if force else self._unauthorized - self._warned
        if warn:
            app = app_config.get_app()
            self.tray_icon.showMessage(
                app.tr("Could not start scheduled updates"),
                app.tr("No users authorized to start:\n") + '\n'.join(map("{0[4]}:{0[3]} - {0[0]}".format, warn))
            )
            self._warned |= warn

    def check_updates(self):
        if self.update is None:
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            app = app_config.get_app()
            urls = self._urls
            unauthorized = self._unauthorized

            for n, upd in enumerate(sorted(self.schedule, key=lambda rec: rec[0])):
                if now >= upd[0]:
                    if (url := urls.get(upd[4], None)) is not None:
                        self.start_update(url.set(database=upd[3]), end=upd[2], start=upd[1])
                        self.tray_icon.showMessage(app.tr("Starting update"),
                                                   self.update_string(upd))
                        del self.schedule[n]
                        self.schedule_store.dump(self.schedule)
                        if upd in unauthorized:
                            unauthorized.remove(upd)
                            if upd in self._warned:
                                self._warned.remove(upd)
                        break
                    else:
                        unauthorized.add(upd)
                else:
                    break
            self.warn_unauthorized_updates(force=False)

    def refresh_updates(self):
        self.schedule = self.schedule_store.refresh()

    @staticmethod
    def update_string(upd: UPDATE_RECORD):
        return f"{upd[0]} {upd[3]}:{upd[4]} Update({upd[1]}-{upd[2]})"

    def schedule_update(self, url: URL, /, dt: datetime.datetime,
                        end: Optional[datetime.datetime] = None, start: Optional[datetime.datetime] = None):
        self.schedule.append((dt, start, end, url.database, url.username))
        self.schedule_store.dump(self.schedule)
        self.register_user(url)

    def cancel_update(self, upd: UPDATE_RECORD):
        check = upd == self.schedule[0]
        self.schedule.remove(upd)
        self.schedule_store.dump(self.schedule)
        if check:
            self.check_updates()

    def start_update(self, url: URL, /,
                     end: Optional[datetime.datetime] = None, start: Optional[datetime.datetime] = None):
        if self.update is not None:
            raise RuntimeError("Other update is in progress.")
        else:
            if self.update_window:
                self.update_window.deleteLater()
            uw = UpdateWindow(self)
            self.update_window = uw
            u = MCHSUpdate(self, url, start, end, max_news_requests=45, retry=1, params={"category": "incidents"})
            self.update = u
            QThreadPool.globalInstance().start(u)

    def _update_finished(self):
        app = app_config.get_app()
        upd = self.update
        rng = upd.range
        self.tray_icon.showMessage(app.tr("Update finished"),
                                   f"{upd.url.database}:{upd.url.username} ({rng[0]}-{rng[1]})")
        del self.update
        self.update = None

    def open_status(self):
        if self.update and self.update_window:
            self.update_window.show()
            self.update_window.raise_()
        else:
            app = app_config.get_app()
            self.tray_icon.showMessage(app.tr("No updates"), app.tr("There are no updates in progress."))

    def open_analysis(self):
        if self.main_window is None:
            self.main_window = MainWindow(self)
        self.main_window.show()
        self.main_window.raise_()

    def close_analysis(self):
        if (mw := self.main_window) is not None:
            mw: MainWindow
            mw.deleteLater()
        self.main_window = None

    @staticmethod
    def close():
        app_config.get_app().exit(0)
