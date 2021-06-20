from typing import *

from sqlalchemy.engine import URL

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCloseEvent
from PyQt5.QtWidgets import QMainWindow, QTabBar

from . import ui_utils
from . import app_config

if not ui_utils.LOAD_UI:
    from .UI.MainWindow import Ui_MainWindow
else:
    Ui_MainWindow = ui_utils.load_ui("MainWindow")

from .connect_menu import ConnectMenu
from .admin_menu import AdminMenu
from .user_menu import UserMenu

if TYPE_CHECKING:
    from .updater import Updater

__all__ = ["MainWindow"]


class MainWindow(Ui_MainWindow, QMainWindow):

    def __init__(self, updater: "Updater"):
        super().__init__()
        self.updater = updater
        self.setupUi(self)

        self.setAttribute(Qt.WA_QuitOnClose, False)
        self.setWindowTitle(app_config.APP_NAME)
        self.setWindowIcon(app_config.ICON)

        self.tabWidget.tabCloseRequested.connect(self.tabWidget.removeTab)

        self.connect_tab = ConnectMenu(self)
        self.tabWidget.addTab(self.connect_tab, self.connect_tab.windowTitle())
        connect_menu_index = self.tabWidget.indexOf(self.connect_tab)

        tab_bar: QTabBar = self.tabWidget.tabBar()
        tab_bar.tabButton(connect_menu_index, QTabBar.RightSide).deleteLater()
        tab_bar.setTabButton(connect_menu_index, QTabBar.RightSide, None)

    def connect(self, url: URL, role: str):
        if role == 'admin':
            tab = AdminMenu(self.updater, url)
        elif role == 'user':
            tab = UserMenu(url)
        else:
            raise ValueError(f"Invalid user role \"{role}\"")
        self.tabWidget.addTab(tab, tab.windowTitle())
        self.tabWidget.setCurrentWidget(tab)

    def closeEvent(self, event: QCloseEvent):
        event.ignore()
        self.updater.close_analysis()
