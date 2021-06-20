from typing import *

from sqlalchemy.engine import Engine, URL
from sqlalchemy import create_engine, inspect, schema

from PyQt5.QtCore import Qt, QSignalBlocker
from PyQt5.QtWidgets import QWidget, QLabel, QLineEdit, QVBoxLayout, QFormLayout, QDialog, QDialogButtonBox

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.AdminMenu import Ui_AdminMenu
else:
    Ui_AdminMenu = ui_utils.load_ui("AdminMenu")

from .schema_menu import SchemaMenu

if TYPE_CHECKING:
    from .updater import Updater

__all__ = ["AdminMenu"]


class AdminMenu(Ui_AdminMenu, QWidget):

    def __init__(self, updater: "Updater", url: URL):
        super().__init__()
        self.updater = updater
        self._engine: Engine = create_engine(url)
        self.setupUi(self)

        self.postfix = self.windowTitle()
        self.setWindowTitle(f"{self._engine.url.username} - {self.postfix}")

        self.schemaMenu = SchemaMenu(self.updater, self._engine.url)
        self.containerSchemaMenu.layout().addWidget(self.schemaMenu)

        self.listSchemas.itemSelectionChanged.connect(
            lambda: self.__class__.selected_schema.__set__(
                self,
                item.text() if (item := self.listSchemas.currentItem()) else None
            ))
        self.listSchemas.itemDoubleClicked.connect(lambda item: self.__class__.open_schema.__set__(self, item.text()))
        self.buttonRefreshSchemas.clicked.connect(self.refresh_schemas)
        self.buttonDeleteSchema.clicked.connect(lambda: self.delete_schema())
        self.buttonCreateSchema.clicked.connect(self.create_schema)
        self.buttonOpenSchema.clicked.connect(
            lambda: self.__class__.open_schema.__set__(
                self,
                None if self.open_schema else self.selected_schema
            ))

        self.refresh_schemas()
        self.open_schema = None

    @property
    def selected_schema(self):
        return items[0].text() if (items := self.listSchemas.selectedItems()) else None

    @selected_schema.setter
    def selected_schema(self, name: Optional[str]):
        ls = self.listSchemas
        b = QSignalBlocker(ls)
        if name:
            if items := ls.findItems(name, Qt.MatchExactly):
                ls.setCurrentItem(items[0])
            else:
                raise KeyError(f"No schema with name \"{name}\" found.")
        else:
            ls.clearSelection()
        del b
        self.buttonDeleteSchema.setEnabled(bool(name))
        if not self.open_schema:
            self.buttonOpenSchema.setEnabled(bool(name))

    def refresh_schemas(self):
        ls = self.listSchemas
        b = QSignalBlocker(ls)
        ls.clear()
        ls.addItems(inspect(self._engine).get_schema_names())
        del b
        self.selected_schema = None

    def delete_schema(self, name: str = None):
        if name is None:
            name = self.selected_schema
        if name is None:
            raise RuntimeError("Schema name should be either provided as argument or selected in schema list.")
        if not self.listSchemas.findItems(name, Qt.MatchExactly):
            raise KeyError(f"No schema with name \"{name}\" found")

        if name == self.open_schema:
            self.open_schema = None
        with self._engine.begin() as con:
            con.execute(schema.DropSchema(name))
        self.refresh_schemas()

    def valid_create_schema(self, name: str) -> bool:
        ls = self.listSchemas
        return bool(name) and name not in (ls.item(i).text() for i in range(ls.count()))

    def create_schema(self):
        d = self.SchemaCreationDialog(self)
        if d.exec_() == QDialog.Accepted:
            with self._engine.begin() as con:
                con.execute(schema.CreateSchema(d.schema))
        self.refresh_schemas()

    @property
    def open_schema(self) -> str:
        return self.schemaMenu.schema

    @open_schema.setter
    def open_schema(self, name: Optional[str]):
        if name and not self.listSchemas.findItems(name, Qt.MatchExactly):
            raise KeyError(f"No schema with name \"{name}\" found")
        self.schemaMenu.schema = name
        # UI
        b = self.buttonOpenSchema
        b.setText(self.tr("Close") if self.open_schema else self.tr("Open"))
        b.setEnabled(bool(self.open_schema or self.selected_schema))

    class SchemaCreationDialog(QDialog):

        def __init__(self, menu: "AdminMenu"):
            super().__init__()
            self.menu = menu

            self.setAttribute(Qt.WA_QuitOnClose, False)

            self.setLayout(QVBoxLayout())

            fl = QFormLayout()
            self.labelScheme = QLabel(self.tr("Scheme name"))
            self.valueScheme = QLineEdit()
            fl.addRow(self.labelScheme, self.valueScheme)
            self.layout().addLayout(fl)

            self.labelError = QLabel()
            self.layout().addWidget(self.labelError)

            self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
            self.layout().addWidget(self.buttons)

            self.valueScheme.textChanged.connect(self._schema_changed)
            self.buttons.accepted.connect(self.accept)
            self.buttons.rejected.connect(self.reject)

            self.setModal(True)
            self.valueScheme.textChanged.emit(self.valueScheme.text())

        @property
        def schema(self) -> str:
            return self.valueScheme.text()

        def _schema_changed(self, name: str):
            valid = self.menu.valid_create_schema(name)

            bb = self.buttons
            for button in bb.buttons():
                if bb.buttonRole(button) == QDialogButtonBox.AcceptRole:
                    button.setEnabled(valid)

            if not valid:
                self.labelError.setText(self.tr("Invalid new schema name."))
            self.labelError.setHidden(valid)
