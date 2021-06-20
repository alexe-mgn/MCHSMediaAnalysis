import logging
import os

from . import ui_utils

from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtWidgets import QApplication

__all__ = ["APP_NAME", "APP", "ICON"]

APP_NAME = "MCHS Media analysis"


class App(QApplication):

    def __init__(self, List):
        super().__init__(List)
        self.setApplicationName(APP_NAME)


if not (APP := QGuiApplication.instance()):
    APP = App([])

APP_NAME = APP.tr(APP_NAME)

if not os.path.isfile(ui_utils.ICON):
    logging.getLogger("UI").error(f"UI icon not found ({ui_utils.ICON})")
    ICON = None
else:
    ICON = QIcon(ui_utils.ICON)
