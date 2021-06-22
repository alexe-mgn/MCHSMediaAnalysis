import logging
import os

import utils

from PyQt5.QtGui import QGuiApplication
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

if not os.path.isfile(utils.PATH.ICON):
    logging.getLogger("UI").error(f"UI icon is not found ({utils.PATH.ICON})")

if not os.path.isfile(utils.PATH.PLOTLY_JS):
    logging.getLogger("UI").error(f"plotly.js is not found ({utils.PATH.PLOTLY_JS})")
