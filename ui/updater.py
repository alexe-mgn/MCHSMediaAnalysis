from typing import *
import datetime

from PyQt5.QtCore import Qt, QThreadPool, QTimer
from sqlalchemy.engine import URL

import utils

from . import app_config

from .schedule_store import ScheduleFileStore
from .qt_updating import MCHSUpdate
from .updater_ui import UpdateWindow, TrayIcon
from .main_window import MainWindow

__all__ = ["UPDATE_RECORD", "UPDATE_RANGE", "Updater"]

UPDATE_RANGE = Tuple[Optional[datetime.datetime], Optional[datetime.datetime]]
# Update start time, lower date, upper date, schema, user
UPDATE_RECORD = Tuple[datetime.datetime,
                      Optional[datetime.datetime], Optional[datetime.datetime],
                      str, str]


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
