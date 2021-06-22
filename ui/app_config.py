import logging
import os

from . import ui_utils

from PyQt5.QtGui import QGuiApplication, QIcon
from PyQt5.QtWidgets import QApplication

__all__ = ["APP_NAME", "get_app"]

APP_NAME = "MCHS Media analysis"


class App(QApplication):

    def __init__(self, List):
        super().__init__(List)
        self.setApplicationName(APP_NAME)


def get_app():
    if not (app := QGuiApplication.instance()):
        app = App([])
    return app


# APP_NAME = APP.tr(APP_NAME)

if not os.path.isfile(ui_utils.ICON_PATH):
    logging.getLogger("UI").error(f"UI icon not found ({ui_utils.ICON_PATH})")
