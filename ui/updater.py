from typing import *
import os
import datetime

import logging
import asyncio

import aiohttp
from PyQt5.QtCore import QRunnable, QThreadPool
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtWidgets import QApplication, QAction, QMenu, QSystemTrayIcon
from sqlalchemy.engine import URL

from utils import PATH
from lib import MCHSUpdater

from . import ui_utils
from . import app_config
from .update_window import UpdateWindow
from .main_window import MainWindow


class QtMCHSUpdater(QRunnable, MCHSUpdater):

    def __init__(self, db_url: URL, loop: asyncio.AbstractEventLoop = None, session: aiohttp.ClientSession = None,
                 max_page_requests: int = None, max_news_requests: int = None, max_requests: int = None):
        super().__init__(db_url, loop, session, max_page_requests, max_news_requests, max_requests)

    def task_started(self, task: MCHSUpdater.AsyncTask, /):
        if isinstance(task, self.PageUpdateTask):
            self.page_requested.emit(task.page)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_requested.emit(task.news_id)

    page_requested = Signal(int)
    news_requested = Signal(int)

    def task_failed(self, task: MCHSUpdater.AsyncTask, /):
        if isinstance(task, self.PageUpdateTask):
            self.page_failed.emit(task.page)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_failed.emit(task.news_id)

    page_failed = Signal(int)
    news_failed = Signal(int)

    def task_successful(self, task: MCHSUpdater.AsyncTask, /):
        if isinstance(task, self.PageUpdateTask):
            self.page_successful.emit(task.page)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_successful.emit(task.news_id)

    page_successful = Signal(int)
    news_successful = Signal(int)

    def task_finished(self, task: MCHSUpdater.AsyncTask, /):
        if isinstance(task, self.PageUpdateTask):
            self.page_finished.emit(task.page)
        elif isinstance(task, self.NewsUpdateTask):
            self.news_finished.emit(task.news_id)

    page_finished = Signal(int)
    news_finished = Signal(int)

    def run(self):
        self.run_all()


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
        super().__init__(app_config.ICON)
        self.updater = updater
        self.setContextMenu(TrayMenu(self.updater))

        self.activated.connect(lambda r: self.updater.open_analysis() if r == QSystemTrayIcon.DoubleClick else ...)


class Updater:

    def __init__(self):
        self.app = QGuiApplication.instance()
        self.tray_icon = TrayIcon(self)
        self.update_window: Optional[UpdateWindow] = None
        self.news_updater: Optional[QtMCHSUpdater] = None
        self.main_window: Optional[MainWindow] = None

        self.tray_icon.show()

    def update(self, url: URL, /, end: Optional[datetime.datetime] = None, start: Optional[datetime.datetime] = None):
        if self.news_updater is not None:
            raise RuntimeError("Other update is in progress.")
        else:
            uw = UpdateWindow(self)
            self.update_window = uw
            nu = QtMCHSUpdater(url)
            self.news_updater = nu

            nu.news_requested.connect(uw.news_requested)
            nu.news_failed.connect(uw.news_failed)
            nu.news_successful.connect(uw.news_successful)
            nu.update_range("date", start, end, ascending=False,
                            params={"category": "incidents"}, retry=1, max_news_requests=45)

            QThreadPool.globalInstance().start(nu)

    def open_status(self):
        if self.update_window:
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

    def close(self):
        self.close_analysis()
        self.app.exit(0)
