from typing import *
import os

import pandas as pd

import plotly

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem
from PyQt5.QtWebEngineWidgets import QWebEngineView

import utils


class TableView(QTableWidget):

    def __init__(self, table: pd.DataFrame = None):
        super().__init__()
        self.table = table

    def update_header(self):
        self.setHorizontalHeaderLabels([self.tr(str(col)) for col in self._table.columns])

    @property
    def table(self) -> Optional[pd.DataFrame]:
        return self._table

    @table.setter
    def table(self, table: Optional[pd.DataFrame]):
        self._table = table
        self.clear()
        if table is not None:
            height, width = table.shape
            self.setRowCount(height)
            self.setColumnCount(width)
            self.update_header()
            for y, (index, row) in enumerate(table.iterrows()):
                for x, v in enumerate(row):
                    item = QTableWidgetItem(str(v))
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                    self.setItem(y, x, item)


class PlotView(QWebEngineView):

    def __init__(self, figure):
        super().__init__()
        self.figure = figure

    @property
    def figure(self):
        return self._figure

    @figure.setter
    def figure(self, figure):
        self._figure = figure
        if figure is not None:
            if not os.path.isfile(utils.PATH.PLOTLY_JS):
                plotly.offline.plot(figure, filename=utils.PATH.PLOT, include_plotlyjs=True, auto_open=False)
                self.load(QUrl.fromLocalFile(utils.PATH.PLOT))
            else:
                self.setHtml(f"""
                <html>
                    <head><meta charset="utf-8"></head>
                    <body>
                        {plotly.offline.plot(figure,
                                             output_type='div',
                                             include_plotlyjs=os.path.relpath(
                                                 utils.PATH.PLOTLY_JS, os.path.dirname(utils.PATH.PLOT)
                                             ))}
                    </body>
                </html>
                """, QUrl.fromLocalFile(utils.PATH.PLOT))
        else:
            self.setHtml(f"<html><body></body></html>")