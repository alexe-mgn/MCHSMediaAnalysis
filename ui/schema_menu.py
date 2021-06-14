from typing import *

from sqlalchemy.engine import Engine, URL
from sqlalchemy import create_engine, inspect, schema, MetaData

from PyQt5.QtCore import Qt, QSignalBlocker
from PyQt5.QtWidgets import QGroupBox

from lib import db

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.SchemaMenu import Ui_SchemaMenu
else:
    Ui_SchemaMenu = ui_utils.load_ui("SchemaMenu")

__all__ = ["SchemaMenu"]


class SchemaMenu(Ui_SchemaMenu, QGroupBox):

    def __init__(self, url: URL = None):
        super().__init__()
        self.engine: Engine = create_engine(url) if url else None
        self.setupUi(self)

        self.listTables.itemSelectionChanged.connect(
            lambda: self.__class__.selected_table.__set__(
                self,
                items[0].text() if (items := self.listTables.selectedItems()) else None
            ))
        self.buttonRefreshTables.clicked.connect(self.refresh_tables)
        self.buttonDeleteTable.clicked.connect(lambda: self.delete_table())
        self.buttonCreateAllTables.clicked.connect(self.create_tables)
        self.buttonDeleteAllTables.clicked.connect(self.delete_tables)

        self.schema = self.schema

    @property
    def schema(self) -> str:
        return self.engine.url.database if self.engine else None

    @schema.setter
    def schema(self, name: Optional[str]):
        name = name if name else None
        if self.engine:
            self.engine = create_engine(self.engine.url._replace(database=name))
        elif name:
            raise RuntimeError("Cannot change schema without engine specified.")

        self.refresh_tables()
        self.setTitle(name if name else "No schema")
        self.tabWidget.setEnabled(bool(name))
        self.buttonRefreshTables.setEnabled(bool(name))
        self.buttonCreateAllTables.setEnabled(bool(name))

    @property
    def selected_table(self) -> str:
        return items[0].text() if (items := self.listTables.selectedItems()) else None

    @selected_table.setter
    def selected_table(self, name: str):
        lt = self.listTables
        b = QSignalBlocker(lt)
        if name:
            if items := lt.findItems(name, Qt.MatchExactly):
                lt.setCurrentItem(items[0])
            else:
                raise KeyError(f"No table with name \"{name}\" found")
        else:
            lt.clearSelection()
        del b
        self.buttonExportTable.setEnabled(bool(name))
        self.buttonImportTable.setEnabled(bool(name))
        self.buttonDeleteTable.setEnabled(bool(name))

    def refresh_tables(self):
        lt = self.listTables
        b = QSignalBlocker(lt)
        lt.clear()
        if self.schema:
            lt.addItems(inspect(self.engine).get_table_names(schema=self.schema))
        del b
        self.selected_table = None
        self.buttonDeleteAllTables.setEnabled(self.listTables.count() > 0)

    def create_tables(self):
        db.Base.metadata.create_all(self.engine)
        self.refresh_tables()

    def delete_tables(self):
        db.Base.metadata.drop_all(self.engine)
        self.refresh_tables()

    def delete_table(self, name: str = None):
        if name is None:
            name = self.selected_table
        if name is None:
            raise RuntimeError("Table name should be either provided as argument or selected in table list.")
        if not self.listTables.findItems(name, Qt.MatchExactly):
            raise KeyError(f"No table with name \"{name}\" found")

        m = MetaData(self.engine)
        m.reflect(only=(name,))

        if (t := m.tables.get(name, None)) is None:
            raise KeyError(f"No table with name \"{name}\" found")
        else:
            t.drop()
        self.refresh_tables()
