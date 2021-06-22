from typing import *
import datetime

import asyncio

import aiohttp
from PyQt5.QtCore import QObject, QRunnable, QThreadPool
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtWidgets import QAction, QMenu, QSystemTrayIcon
from sqlalchemy.engine import URL

import utils

from lib import MCHSUpdater

from .update_window import UpdateWindow
from .main_window import MainWindow


__all__ = ["UPDATE_RANGE", "Updater"]


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


class TrayMenu(QMenu):

    def __init__(self, updater: "Updater"):
        super().__init__()
        self.updater = updater

        self.actionShowStatus = QAction("Show update status")
        self.actionShowStatus.triggered.connect(self.updater.open_status)
        self.addAction(self.actionShowStatus)

        self.actionShowMain = QAction("Open analysis")
        self.actionShowMain.triggered.connect(self.updater.open_analysis)
        self.addAction(self.actionShowMain)

        self.actionExit = QAction("Exit")
        self.actionExit.triggered.connect(self.updater.close)
        self.addAction(self.actionExit)


class TrayIcon(QSystemTrayIcon):

    def __init__(self, updater: "Updater"):
        super().__init__(QIcon(utils.PATH.ICON))
        self.updater = updater
        self.setContextMenu(TrayMenu(self.updater))

        self.activated.connect(lambda r: self.updater.open_analysis() if r == QSystemTrayIcon.DoubleClick else ...)


class Updater:

    def __init__(self):
        self.app = QGuiApplication.instance()
        self.tray_icon = TrayIcon(self)
        self.update_window: Optional[UpdateWindow] = None
        self.update: Optional[MCHSUpdate] = None
        self.main_window: Optional[MainWindow] = None

        self.tray_icon.show()

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
        del self.update
        self.update = None

    def open_status(self):
        if self.update and self.update_window:
            self.update_window.show()
            self.update_window.raise_()
        else:
            self.tray_icon.showMessage("No updates", "There are no updates in progress.")

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
        self.tray_icon.showMessage(
            "Background task",
            "MCHS Media updater utility is running in background mode to execute scheduled updates.")

    def close(self):
        self.app.exit(0)
