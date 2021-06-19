from typing import *
import datetime

from sqlalchemy.sql.expression import func
import sqlalchemy.orm
from sqlalchemy.engine import Engine, URL
from sqlalchemy import create_engine, inspect, MetaData

from PyQt5.QtCore import Qt, QSignalBlocker
from PyQt5.QtWidgets import QGroupBox

from lib import db
from lib.date_utils import MCHS_TZ

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.SchemaMenu import Ui_SchemaMenu
else:
    Ui_SchemaMenu = ui_utils.load_ui("SchemaMenu")

if TYPE_CHECKING:
    from .updater import UPDATE_RANGE, Updater

__all__ = ["SchemaMenu"]


class SchemaMenu(Ui_SchemaMenu, QGroupBox):

    def __init__(self, updater: "Updater", url: URL = None):
        super().__init__()
        self.updater = updater
        self.engine: Engine = create_engine(url) if url else None
        self.setupUi(self)
        self.tabWidget.setCurrentIndex(0)

        # Tables
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

        # Update
        self.checkUpdateToLast.stateChanged.connect(lambda state: self.valueUpdateDateA.setEnabled(not state))
        self.valueUpdateDateA.dateTimeChanged.connect(
            lambda dt: self.valueUpdateDateB.setDateTime(max(self.valueUpdateDateB.dateTime(), dt)))

        self.checkUpdateFromAny.stateChanged.connect(lambda state: self.valueUpdateDateB.setEnabled(not state))
        self.checkUpdateFromAny.stateChanged.connect(lambda state: self.buttonSetDateNow.setEnabled(not state))
        self.valueUpdateDateB.dateTimeChanged.connect(
            lambda dt: self.valueUpdateDateA.setDateTime(min(self.valueUpdateDateA.dateTime(), dt)))
        self.buttonSetDateNow.clicked.connect(
            lambda: self.valueUpdateDateB.setDateTime(
                ui_utils.QDateTime_fromPyDateTime(datetime.datetime.now(MCHS_TZ))
            ))

        self.valueUpdateDateA.setDateTime(ui_utils.QDateTime_fromPyDateTime(
            datetime.datetime.now(MCHS_TZ) - datetime.timedelta(days=30)))
        self.checkUpdateToLast.stateChanged.emit(self.checkUpdateToLast.checkState())
        self.checkUpdateFromAny.stateChanged.emit(self.checkUpdateFromAny.checkState())

        self.buttonUpdate.clicked.connect(self.update_now)

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

    def get_update_range(self) -> Tuple[datetime.datetime, datetime.datetime]:
        return (self.valueUpdateDateA.dateTime().toPyDateTime().replace(tzinfo=MCHS_TZ) if
                not self.checkUpdateToLast.checkState() else None,
                self.valueUpdateDateB.dateTime().toPyDateTime().replace(tzinfo=MCHS_TZ) if
                not self.checkUpdateFromAny.checkState() else None)

    def update_now(self):
        a, b = self.get_update_range()
        if a is None:
            with self.engine.connect() as con:
                con: sqlalchemy.orm.Session
                a = con.execute(func.max(db.News.date)).scalar()
        if a is not None:
            a = a.replace(tzinfo=MCHS_TZ)
        self.updater.start_update(self.engine.url, b, a)
        self.updater.open_status()
