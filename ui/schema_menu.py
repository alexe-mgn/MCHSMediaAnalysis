from typing import *
import datetime

import csv

from sqlalchemy.sql.expression import func
from sqlalchemy.engine import Engine, URL
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, inspect, MetaData

from PyQt5.QtCore import Qt, QSignalBlocker
from PyQt5.QtWidgets import QGroupBox, QTableWidgetItem, QFileDialog

from lib import db
from lib.date_utils import MCHS_TZ

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.SchemaMenu import Ui_SchemaMenu
else:
    Ui_SchemaMenu = ui_utils.load_ui("SchemaMenu")

from .error_dialog import raise_exc_dialog

if TYPE_CHECKING:
    from .updater import UPDATE_RECORD, UPDATE_RANGE, Updater

__all__ = ["SchemaMenu"]


class SchemaMenu(Ui_SchemaMenu, QGroupBox):

    def __init__(self, updater: "Updater", url: URL = None):
        super().__init__()
        self.updater = updater
        self._engine: Engine = create_engine(url) if url else None
        self._schedule: List["UPDATE_RECORD"] = []
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
        self.buttonExportTable.clicked.connect(lambda: self.export_table())
        self.buttonImportTable.clicked.connect(lambda: self.import_table())
        self.buttonCreateAllTables.clicked.connect(self.create_tables)
        self.buttonDeleteAllTables.clicked.connect(self.delete_tables)

        # Update controls
        self.checkUpdateToLast.stateChanged.connect(lambda state: self.valueUpdateDateA.setEnabled(not state))
        self.valueUpdateDateA.dateTimeChanged.connect(
            lambda dt: self.valueUpdateDateB.setDateTime(max(self.valueUpdateDateB.dateTime(), dt)))

        self.checkUpdateFromAny.stateChanged.connect(lambda state: self.valueUpdateDateB.setEnabled(not state))
        self.checkUpdateFromAny.stateChanged.connect(lambda state: self.buttonSetDateNow.setEnabled(not state))
        self.valueUpdateDateB.dateTimeChanged.connect(
            lambda dt: self.valueUpdateDateA.setDateTime(min(self.valueUpdateDateA.dateTime(), dt)))
        self.buttonSetDateNow.clicked.connect(
            lambda: self.valueUpdateDateB.setDateTime(
                ui_utils.qdatetime_frompydatetime(datetime.datetime.now(MCHS_TZ))
            ))

        self.valueUpdateDateA.setDateTime(ui_utils.qdatetime_frompydatetime(
            datetime.datetime.now(MCHS_TZ) - datetime.timedelta(days=30)))
        self.checkUpdateToLast.stateChanged.emit(self.checkUpdateToLast.checkState())
        self.checkUpdateFromAny.stateChanged.emit(self.checkUpdateFromAny.checkState())

        self.buttonUpdate.clicked.connect(self.ui_update_now)

        # Schedule
        self.buttonScheduleDateNow.clicked.connect(
            lambda: self.valueScheduleDate.setDateTime(
                ui_utils.qdatetime_frompydatetime(datetime.datetime.now().astimezone())
            ))

        self.buttonRefreshSchedule.clicked.connect(self.refresh_schedule)
        self.buttonSchedule.clicked.connect(self.ui_schedule_update)

        self.tableSchedule.itemSelectionChanged.connect(
            lambda: self.buttonScheduleCancel.setEnabled(bool(self.tableSchedule.selectedItems())))

        self.buttonScheduleCancel.clicked.connect(self.ui_cancel_selected_updates)

        self.valueScheduleDate.setDateTime(ui_utils.qdatetime_frompydatetime(
            datetime.datetime.now().astimezone() + datetime.timedelta(hours=1)
        ))

        self.schema = self.schema

    @property
    def schema(self) -> str:
        return self._engine.url.database if self._engine else None

    @schema.setter
    def schema(self, name: Optional[str]):
        name = name if name else None
        if self._engine:
            self._engine = create_engine(self._engine.url._replace(database=name))
        elif name:
            raise RuntimeError("Cannot change schema without engine specified.")

        self.refresh_tables()
        self.refresh_schedule()
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
            lt.addItems(inspect(self._engine).get_table_names(schema=self.schema))
        del b
        self.selected_table = None
        self.buttonDeleteAllTables.setEnabled(self.listTables.count() > 0)

    def refresh_schedule(self):
        self._schedule.clear()
        ts = self.tableSchedule
        b = QSignalBlocker(ts)
        ts.clear()
        user = self._engine.url.username
        schema = self.schema
        updates = [upd for upd in self.updater.schedule if upd[3] == schema and upd[4] == user]
        ts.setRowCount(len(updates))
        ts.setHorizontalHeaderLabels(
            [self.tr(e) for e in ("update time", "start", "end", "schema", "user")])
        for y, upd in enumerate(updates):
            self._schedule.append(upd)
            for x, i in enumerate(upd):
                item = QTableWidgetItem(str(i))
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                ts.setItem(y, x, item)
        del b

    def create_tables(self):
        db.Base.metadata.create_all(self._engine)
        self.refresh_tables()

    def delete_tables(self):
        db.Base.metadata.drop_all(self._engine)
        self.refresh_tables()

    def _check_table(self, name: str = None):
        if name is None:
            name = self.selected_table
        if name is None:
            raise RuntimeError("Table name should be either provided as argument or selected in table list.")
        if not self.listTables.findItems(name, Qt.MatchExactly):
            raise KeyError(f"No table with name \"{name}\" found")
        return name

    def delete_table(self, name: str = None):
        name = self._check_table(name)

        m = MetaData(self._engine)
        m.reflect(only=(name,))

        if (t := m.tables.get(name, None)) is None:
            raise KeyError(f"No table with name \"{name}\" found")
        else:
            t.drop()
        self.refresh_tables()

    def export_table(self, name: str = None):
        name = self._check_table(name)
        d = QFileDialog(caption=self.tr("Export table"), filter="CSV (*.csv)")
        d.setAcceptMode(QFileDialog.AcceptSave)
        d.setAttribute(Qt.WA_QuitOnClose, False)
        if d.exec_():
            with open(d.selectedFiles()[0], mode='w', newline='') as file:
                writer = csv.writer(file)
                m = MetaData(self._engine)
                m.reflect(only=(name,))
                if (t := m.tables.get(name, None)) is None:
                    raise KeyError(f"No table with name \"{name}\" found")
                else:
                    with Session(self._engine) as s:
                        cols = t.columns
                        for row in s.query(t).all():
                            writer.writerow(row[col.name] for col in cols)

    def import_table(self, name: str = None):
        name = self._check_table(name)
        d = QFileDialog(caption=self.tr("Import table"), filter="CSV (*.csv)")
        d.setAcceptMode(QFileDialog.AcceptOpen)
        d.setFileMode(QFileDialog.ExistingFile)
        d.setAttribute(Qt.WA_QuitOnClose, False)
        if d.exec_():
            with open(d.selectedFiles()[0], mode='r') as file:
                reader = csv.reader(file)
                m = MetaData(self._engine)
                m.reflect(only=(name,))
                if (t := m.tables.get(name, None)) is None:
                    raise KeyError(f"No table with name \"{name}\" found")
                else:
                    with Session(self._engine) as s, s.begin():
                        cols = t.columns
                        s.execute(t.delete())
                        for row in reader:
                            s.execute(t.insert(values={k.name: v for k, v in zip(cols, row)}))

    def _get_ui_update_range(self) -> Tuple[datetime.datetime, datetime.datetime]:
        return (self.valueUpdateDateA.dateTime().toPyDateTime().replace(second=0, tzinfo=MCHS_TZ) if
                not self.checkUpdateToLast.checkState() else None,
                self.valueUpdateDateB.dateTime().toPyDateTime().replace(second=0, tzinfo=MCHS_TZ) if
                not self.checkUpdateFromAny.checkState() else None)

    def ui_get_update_range(self) -> "UPDATE_RANGE":
        a, b = self._get_ui_update_range()
        if a is None:
            with self._engine.connect() as con:
                a = con.execute(func.max(db.News.date)).scalar()
        if a is not None:
            a = a.replace(tzinfo=MCHS_TZ)
        return a, b

    def ui_update_now(self):
        try:
            a, b = self.ui_get_update_range()
            self.updater.start_update(self._engine.url, b, a)
        except RuntimeError:
            raise_exc_dialog()
        else:
            self.updater.open_status()

    def ui_schedule_update(self):
        try:
            a, b = self.ui_get_update_range()
            self.updater.schedule_update(
                self._engine.url,
                self.valueScheduleDate.dateTime().toPyDateTime().astimezone().replace(second=0),
                b, a)
        except RuntimeError:
            raise_exc_dialog()
        self.refresh_schedule()

    def ui_cancel_selected_updates(self):
        schedule = self._schedule
        upds = {schedule[ind.row()] for ind in self.tableSchedule.selectedIndexes()}
        updater = self.updater
        for upd in upds:
            if upd in updater.schedule:
                updater.cancel_update(upd)
        self.refresh_schedule()
