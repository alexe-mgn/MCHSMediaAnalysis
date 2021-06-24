from typing import *
import os
import itertools as it

from sqlalchemy.engine import URL

import numpy as np
import pandas as pd

import plotly.offline
import plotly.express
import plotly

from PyQt5.QtWidgets import QWidget, QLabel, QComboBox

from lib import analysis

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.UserMenu import Ui_UserMenu
else:
    Ui_UserMenu = ui_utils.load_ui("UserMenu")

from .user_menu_views import TableView, PlotView


class UserMenu(Ui_UserMenu, QWidget):

    def __init__(self, url: URL):
        super().__init__()
        self._tables: Dict[str, TableView] = {}

        self.url = url
        self.setupUi(self)
        self.plot_var_widgets: List[Tuple[QLabel, QComboBox]] = [
            (self.labelPlot1, self.valuePlot1),
            (self.labelPlot2, self.valuePlot2),
            (self.labelPlot3, self.valuePlot3),
            (self.labelPlot4, self.valuePlot4)
        ]

        self.postfix = self.windowTitle()
        self.setWindowTitle(f"{self.url.database}:{self.url.username} - {self.postfix}")

        # Tables
        for t_type in ("pivot", "contingency"):
            self.valueTableType.addItem(self.tr(t_type), t_type)

        self.buttonRefreshNews.clicked.connect(lambda: self.set_table(
            "news",
            analysis.read_dataframe(self.url, limit=n if (n := self.valueLimitNews.value()) != -1 else None)[
                ["id", "date", "title", "text", "type",
                 "region", "city", "injuries", "n_staff", "n_tech",
                 "tags", "area", "water"]
            ]
        ))

        self.valueTableSource.currentTextChanged.connect(self._set_table_controls)
        self.valueTableType.currentIndexChanged.connect(
            lambda i: self._set_table_type(self.valueTableType.itemData(i)))

        self.buttonTable.clicked.connect(self.ui_create_table)

        self.tabWidgetTables.currentChanged.connect(lambda i: self.buttonTableExport.setDisabled(i == -1))
        self.tabWidgetTables.tabCloseRequested.connect(
            lambda i: self.delete_table(
                next(k for k, v in self._tables.items() if v is self.tabWidgetTables.widget(i))
            ))

        self.valueTableSource.currentTextChanged.emit(self.valueTableSource.currentText())
        self.tabWidgetTables.currentChanged.emit(self.tabWidgetTables.currentIndex())
        # TODO export

        # Plots
        for p_type in self.plot_arguments.keys():
            self.valuePlotType.addItem(self.tr(p_type), p_type)

        self.valuePlotTable.currentTextChanged.connect(self._set_plot_controls)
        self.valuePlotType.currentIndexChanged.connect(lambda i: self._set_plot_type(self.valuePlotType.itemData(i)))
        self.buttonPlot.clicked.connect(self.ui_plot)

        self.tabWidgetPlots.currentChanged.connect(lambda i: self.buttonPlotExport.setDisabled(i == -1))
        self.tabWidgetPlots.tabCloseRequested.connect(self.tabWidgetPlots.removeTab)

        self.valuePlotTable.currentTextChanged.emit(self.valuePlotTable.currentText())
        self.tabWidgetPlots.currentChanged.emit(self.tabWidgetPlots.currentIndex())

    def _set_table_controls(self, name: Optional[str]):
        enabled = bool(name)
        for i in (self.valueTableType, self.valueTableName, self.buttonTable):
            i.setEnabled(enabled)
        self._set_table_type(self.valueTableType.currentData() if enabled else None)

        variables = list(self._tables[name].table.columns) if enabled else []
        for i in (self.valueTableRows, self.valueTableColumns, self.valueTableValues):
            t = i.currentText()
            i.clear()
            for v in variables:
                i.addItem(self.tr(str(v)), v)
            i.setCurrentText(t)

    def _set_table_type(self, t_type: Optional[str]):
        enabled = bool(t_type)
        for i in (self.valueTableRows, self.valueTableColumns):
            i.setEnabled(enabled)
        self.labelTableValues.setHidden(not enabled or t_type != 'pivot')
        self.valueTableValues.setHidden(not enabled or t_type != 'pivot')

    def _set_plot_controls(self, name: Optional[str]):
        enabled = bool(name)
        for i in (self.valuePlotType, self.valuePlotName, self.buttonPlot):
            i.setEnabled(enabled)
        self._set_plot_type(self.valuePlotType.currentData() if enabled else None)

        variables = list(self._tables[name].table.columns) if enabled else []
        for label, value in self.plot_var_widgets:
            t = value.currentText()
            value.clear()
            value.addItem("", None)
            for v in variables:
                value.addItem(self.tr(str(v)), v)
            value.setCurrentText(t)
        # self.valuePlotColor.insertItem(0, "", None)
        # self.valuePlotColor.setCurrentText("")

    # None for ['x', 'y', 'color']
    plot_arguments_default = ['x', 'y', 'color']
    plot_arguments = {
        "scatter": ['x', 'y', 'color', 'size'],
        "line": ['x', 'y', 'color', 'line_group'],
        "area": ['x', 'y', 'color', 'line_group'],
        "bar": None,
        "pie": ['names'],
        "histogram": None,
        "box": None,
        "density_contour": None,
        "density_heatmap": ['x', 'y']
    }

    def _set_plot_type(self, name: Optional[str]):
        if not name:
            for label, value in self.plot_var_widgets:
                label.setHidden(True)
                value.setHidden(True)
        else:
            for arg, (label, value) in it.zip_longest(
                    args if (args := self.plot_arguments[name]) is not None else self.plot_arguments_default,
                    self.plot_var_widgets,
                    fillvalue=None):
                label.setHidden(arg is None)
                label.setText(arg)
                value.setHidden(arg is None)

    # TODO TRANSLATIONS
    def set_table(self, name: str, table: pd.DataFrame):
        if name in self._tables:
            self.delete_table(name)
        tv = TableView(table)
        self._tables[name] = tv
        self.tabWidgetTables.addTab(tv, name)
        for i in (self.valueTableSource, self.valuePlotTable):
            i.addItem(name)

    def select_table(self, name: str):
        self.tabWidgetTables.setCurrentWidget(self._tables[name])

    def delete_table(self, name: str):
        self.tabWidgetTables.removeTab(
            self.tabWidgetTables.indexOf(
                self._tables.pop(name)))
        for i in (self.valueTableSource, self.valuePlotTable):
            i.removeItem(i.findText(name))

    def create_plot(self, figure, name: Optional[str] = None):
        self.tabWidgetPlots.addTab(PlotView(figure), name if name is not None else "")

    def ui_create_table(self):
        if not (name := self.valueTableName.currentText()):
            raise ValueError(f"Table name can't be empty.")
        source = self._tables[self.valueTableSource.currentText()].table
        t_type = self.valueTableType.currentData()
        rows = self.valueTableRows.currentData()
        cols = self.valueTableColumns.currentData()
        if t_type == 'pivot':
            table = pd.pivot_table(source, values=self.valueTableValues.currentData(), index=rows, columns=cols)
        elif t_type == 'contingency':
            table = pd.crosstab(source[rows], source[cols])
        else:
            raise ValueError(f"Invalid table type {t_type}.")
        self.set_table(name, table)
        self.select_table(name)

    def ui_plot(self):
        table = self._tables[self.valuePlotTable.currentText()].table.replace({pd.NA: np.nan})
        p_type = self.valuePlotType.currentData()
        name = self.valuePlotName.text()
        plot_args = {arg: value.currentData() for arg, (label, value) in
                     zip(self.plot_arguments[p_type] if
                         self.plot_arguments[p_type] is not None else
                         self.plot_arguments_default,
                         self.plot_var_widgets)}
        if 'size' in plot_args:
            table.fillna({plot_args['size']: 0}, inplace=True)
        if p_type == 'pie':
            fig = plotly.express.pie(table, **plot_args)
        else:
            fig = plotly.plot(table, p_type, **plot_args)
        self.create_plot(fig, name)
        for i in range(self.tabWidgetPlots.count()):
            if getattr(self.tabWidgetPlots.widget(i), "figure", None) == fig:
                self.tabWidgetPlots.setCurrentIndex(i)
                break
