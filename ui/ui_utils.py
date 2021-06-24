from typing import *

import logging
import datetime

from PyQt5.QtCore import QDateTime, QTimeZone
from PyQt5.QtGui import QGuiApplication
from PyQt5.QtWidgets import QApplication, QWidget
from PyQt5 import uic

from utils import PATH, FROZEN

LOAD_UI = False

UI_CLASSES = ["ErrorDialog",
              "UpdateWindow", "MainWindow",
              "ConnectMenu",
              "AdminMenu", "SchemaMenu",
              "UserMenu"]

_UI_UPDATED = FROZEN or LOAD_UI


def get_ui(cls: str, py=False):
    return f"{PATH.UI}/{cls}.{'py' if py else 'ui'}"


def load_ui(cls: str):
    return uic.loadUiType(get_ui(cls, py=False))[0]


def update_ui(cls: str):
    logging.debug(f"Updating {cls} ui")
    with open(get_ui(cls, py=True), mode='w') as pyfile:
        uic.compileUi(get_ui(cls, py=False), pyfile)


def update_all_ui():
    logging.debug("Updating all ui classes")
    for cls in UI_CLASSES:
        update_ui(cls)


def update_all_ui_once():
    global _UI_UPDATED
    if not _UI_UPDATED:
        update_all_ui()
        _UI_UPDATED = True


def test_ui(widget: Union[QWidget, Type[QWidget], Callable], *args, **kwargs):
    if not (app := QGuiApplication.instance()):
        app = QApplication([])
    if not isinstance(widget, QWidget):
        widget = widget()
    widget.show()
    if not app.startingUp():
        app.exec_()


def qdatetime_frompydatetime(dt: datetime.datetime):
    return QDateTime.fromSecsSinceEpoch(dt.timestamp()) if \
        dt.tzinfo is None else \
        QDateTime.fromSecsSinceEpoch(dt.timestamp(), QTimeZone(dt.tzinfo.utcoffset(None).seconds))
