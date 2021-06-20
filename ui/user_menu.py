from sqlalchemy.engine import Engine, URL
from sqlalchemy import create_engine

from PyQt5.QtWidgets import QWidget

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.UserMenu import Ui_UserMenu
else:
    Ui_UserMenu = ui_utils.load_ui("UserMenu")


class UserMenu(Ui_UserMenu, QWidget):

    def __init__(self, url: URL):
        super().__init__()
        self.engine: Engine = create_engine(url)
        self.setupUi(self)

        self.postfix = self.windowTitle()
        self.setWindowTitle(f"{self.engine.url.database}:{self.engine.url.username} - {self.postfix}")
