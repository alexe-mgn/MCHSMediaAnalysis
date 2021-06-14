from typing import *

import logging

from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5 import uic

from utils import PATH, FROZEN

LOAD_UI = False

UI_CLASSES = ["MainWindow", "ErrorDialog",
              "ConnectMenu",
              "AdminMenu", "SchemaMenu"]

_UI_UPDATED = FROZEN


def get_ui(cls: str, py=False):
    return f"{PATH.UI}/{cls}.{'py' if py else 'ui'}"


def load_ui(cls: str):
    return uic.loadUiType(get_ui(cls, py=False))[0]


def update_ui(cls: str):
    logging.debug(f"Updating {cls} ui")
    with open(get_ui(cls, py=True), mode='w') as pyfile:
        uic.compileUi(get_ui(cls, py=False), pyfile)


def update_all_ui_once():
    global _UI_UPDATED
    if not _UI_UPDATED:
        logging.debug("Updating all ui classes")
        for cls in UI_CLASSES:
            update_ui(cls)
        _UI_UPDATED = True


def test_ui(widget: Union[QWidget, Type[QWidget], Callable], *args, **kwargs):
    if not (app := QGuiApplication.instance()):
        app = QApplication([])
    if not isinstance(widget, QWidget):
        widget = widget()
    widget.show()
    if not app.startingUp():
        app.exec_()
