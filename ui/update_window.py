from typing import *

from PyQt5.QtCore import pyqtSlot as Slot
from PyQt5.QtWidgets import QWidget

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.UpdateWindow import Ui_UpdateWindow
else:
    Ui_UpdateWindow = ui_utils.load_ui("UpdateWindow")

if TYPE_CHECKING:
    # from lib import
    from .updater import Updater


class UpdateWindow(Ui_UpdateWindow, QWidget):

    def __init__(self, updater: "Updater"):
        super().__init__()
        self.updater = updater

        self.setupUi(self)

    @Slot(int)
    def news_requested(self, news_id: int):
        v = self.valuePending
        v.display(v.intValue() + 1)

    @Slot(int)
    def news_failed(self, news_id: int):
        v = self.valueFailed
        v.display(v.intValue() + 1)
        p = self.valuePending
        p.display(p.intValue() - 1)

    @Slot(int)
    def news_successful(self, news_id: int):
        v = self.valueSuccessful
        v.display(v.intValue() + 1)
        p = self.valuePending
        p.display(p.intValue() - 1)

    # @Slot(int)
    # def news_finished(self, news_id: int):
    #     ...
