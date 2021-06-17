from typing import *
import os
import datetime

import logging
import asyncio

import aiohttp
from PyQt5.QtCore import pyqtSignal as Signal
from PyQt5.QtCore import QRunnable, QThreadPool
from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon
from sqlalchemy.engine import URL

from utils import PATH
from lib import MCHSUpdater

from . import ui_utils
from .update_window import UpdateWindow


class Updater:

    class NewsUpdater(MCHSUpdater):

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

        def task_finished(self, task: MCHSUpdater.AsyncTask, /):
            if isinstance(task, self.PageUpdateTask):
                self.page_finished.emit(task.page)
            elif isinstance(task, self.NewsUpdateTask):
                self.news_finished.emit(task.news_id)

        page_finished = Signal(int)
        news_finished = Signal(int)

        def task_successful(self, task: MCHSUpdater.AsyncTask, /):
            if isinstance(task, self.PageUpdateTask):
                self.page_successful.emit(task.page)
            elif isinstance(task, self.NewsUpdateTask):
                self.news_successful.emit(task.news_id)

        page_successful = Signal(int)
        news_successful = Signal(int)

        def task_failed(self, task: MCHSUpdater.AsyncTask, /):
            if isinstance(task, self.PageUpdateTask):
                self.page_failed.emit(task.page)
            elif isinstance(task, self.NewsUpdateTask):
                self.news_failed.emit(task.news_id)

        page_failed = Signal(int)
        news_failed = Signal(int)

    def __init__(self):
        if not os.path.isfile(ui_utils.ICON):
            logging.getLogger("UI").error(f"UI icon not found ({ui_utils.ICON})")
            icon = None
        else:
            icon = QIcon(ui_utils.ICON)
        self.tray_icon = QSystemTrayIcon(icon)
        self.tray_icon.show()

    def update(self, url: URL, /, end: Optional[datetime.datetime] = None, start: Optional[datetime.datetime] = None):
        self.update_window = UpdateWindow(self)
        nu = self.NewsUpdater(url)
        self.news_updater = nu
