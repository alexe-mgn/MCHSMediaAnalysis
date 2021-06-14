from typing import TYPE_CHECKING

from PyQt5.QtCore import QSignalBlocker
from PyQt5.QtWidgets import QWidget
from sqlalchemy.engine import create_engine, URL

from . import ui_utils
from .error_dialog import raise_exc_dialog

if not ui_utils.LOAD_UI:
    from .UI.ConnectMenu import Ui_ConnectMenu
else:
    Ui_ConnectMenu = ui_utils.load_ui("ConnectMenu")

if TYPE_CHECKING:
    from .main_window import MainWindow

__all__ = ["ConnectMenu"]


class ConnectMenu(Ui_ConnectMenu, QWidget):

    def __init__(self, main: "MainWindow"):
        super().__init__()
        self.main = main
        self.setupUi(self)

        if (user := self.valueRole.findText(self.tr("user"))) != -1:
            self.valueRole.setItemData(user, "user")
        if (admin := self.valueRole.findText(self.tr("admin"))) != -1:
            self.valueRole.setItemData(admin, "admin")

        self.valueRole.currentIndexChanged.connect(
            lambda ind: self.__class__.role.__set__(self, self.valueRole.itemData(ind))
        )
        self.checkAdvanced.stateChanged.connect(self.toggle_advanced)
        self.buttonConnect.clicked.connect(self.connect)

        self.role = "user"
        self.toggle_advanced(False)

        # self.adjustSize()

    @property
    def role(self) -> str:
        return self.valueRole.currentData()

    @role.setter
    def role(self, r: str):
        if (ind := self.valueRole.findData(r)) != -1:
            b = QSignalBlocker(self.valueRole)
            self.valueRole.setCurrentIndex(ind)
            del b
            scheme_req = r == "user"
            self.labelSchema.setHidden(not scheme_req)
            self.valueSchema.setHidden(not scheme_req)
        else:
            raise KeyError(f'Invalid user role "{r}"')
        # self.adjustSize()

    def toggle_advanced(self, expand: bool = None):
        if expand is None:
            expand = not self.checkAdvanced.isChecked()
        b = QSignalBlocker(self.checkAdvanced)
        self.checkAdvanced.setChecked(expand)
        del b
        self.groupAdvanced.setHidden(not expand)
        # self.adjustSize()

    def connect(self):
        server = server if (server := self.valueServer.text()) else self.valueServer.placeholderText()
        host, *port = server.rsplit(':', 1)
        if port and (port := port[0]).isdigit():
            port = int(port)
        else:
            host = server
            port = None
        try:
            if self.role == 'user':
                if not (schema_name := self.valueSchema.text()):
                    raise ValueError("Schema name should be provided for user connection.")
            else:
                schema_name = None
            url = URL.create(
                drivername=f"{self.valueEngine.currentText().lower()}+{self.valueConnector.currentText().lower()}",
                username=user if (user := self.valueUser.text()) else self.valueUser.placeholderText(),
                password=self.valuePassword.text() if self.valuePassword.text() else None,
                host=host, port=port,
                database=schema_name)
            with create_engine(url).connect():
                pass
            self.main.connect(url, self.role)
        except:
            raise_exc_dialog()
        else:
            self.valueUser.clear()
            self.valuePassword.clear()
