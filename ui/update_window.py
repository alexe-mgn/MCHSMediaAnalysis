from typing import *
import traceback
import datetime

from PyQt5.QtCore import Qt
from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget

from . import ui_utils
from lib.parsing import NEWS_DICT

if not ui_utils.LOAD_UI:
    from .UI.UpdateWindow import Ui_UpdateWindow
else:
    Ui_UpdateWindow = ui_utils.load_ui("UpdateWindow")

if TYPE_CHECKING:
    from .updater import UPDATE_RANGE, Updater

__all__ = ["UpdateWindow"]


class UpdateWindow(Ui_UpdateWindow, QWidget):

    def __init__(self, updater: "Updater"):
        super().__init__()
        self.updater = updater
        self.__range: "UPDATE_RANGE" = (None, None)
        self._maximum = None
        self.__current: Optional[datetime.datetime] = None
        self.setupUi(self)

        self.setAttribute(Qt.WA_QuitOnClose, False)

    @property
    def _range(self) -> "UPDATE_RANGE":
        return self.__range

    @_range.setter
    def _range(self, rng: "UPDATE_RANGE"):
        self.__range = rng
        self.labelB.setText(str(rng[0]) if rng[0] is not None else '?')
        self.labelA.setText(str(rng[1]) if rng[1] is not None else '?')

    @property
    def _current(self) -> Optional[datetime.datetime]:
        return self.__current

    @_current.setter
    def _current(self, date: datetime.datetime):
        self.__current = date
        self.labelCurrent.setText(str(date) if date is not None else '?')
        self.refresh_progress()

    def refresh_progress(self):
        lower, upper = self._range
        upper = upper if upper is not None else self._maximum
        if lower is not None:
            if upper is not None:
                p = round((upper - self._current).total_seconds() * 100 / (upper - lower).total_seconds())
            else:
                p = 0
        else:
            p = round(self.valuePending.intValue() * 100
                      / (self.valuePending.intValue() + self.valueFailed.intValue() + self.valueSuccessful.intValue()))
        self.progressBar.setValue(p)

    @Slot(int)
    def page_requested(self, page: int):
        self.valuePage.display(page)

    @Slot(int)
    def news_requested(self, news_id: int):
        v = self.valuePending
        v.display(v.intValue() + 1)

    @Slot(object, object, object)
    def task_raised(self, etype: Type[BaseException] = None, evalue: BaseException = None, etraceback=None):
        self.errorLogBrowser.append(''.join(traceback.format_exception(etype, evalue, etraceback)))
        self.errorLogBrowser.append('\n' + '-' * 20 + '\n\n')

    @Slot(int, object, object, object)
    def news_failed(self, news_id: int,
                    etype: Type[BaseException] = None, evalue: BaseException = None, etraceback=None):
        v = self.valueFailed
        v.display(v.intValue() + 1)
        p = self.valuePending
        p.display(p.intValue() - 1)

    @Slot(int, dict)
    def news_successful(self, news_id: int, news: NEWS_DICT = None):
        v = self.valueSuccessful
        v.display(v.intValue() + 1)
        p = self.valuePending
        p.display(p.intValue() - 1)
        if news and (date := news.get('date', None)) is not None:
            if self._range[1] is None and (self._maximum is None or date > self._maximum):
                self._maximum = date
                self.labelA.setText(str(date))
            if self._current is None or date < self._current:
                self._current = date

    # @Slot(int)
    # def news_finished(self, news_id: int):
    #     ...

    @Slot()
    def update_started(self):
        if (u := self.updater.update) is not None:
            self._range = u.range
            self.buttonAbort.setEnabled(True)
            self.buttonAbort.clicked.connect(u.stop)
        else:
            self.buttonAbort.setDisabled(True)
        self.progressBar.setValue(0)
        self.buttonAbort.setText(self.tr("Abort"))

    @Slot()
    def update_finished(self):
        self.progressBar.setValue(100)
        self.buttonAbort.setDisabled(True)
