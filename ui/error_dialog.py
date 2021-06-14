from typing import *
import sys
import traceback

from PyQt5.QtWidgets import QDialog

from . import ui_utils

if not ui_utils.LOAD_UI:
    from .UI.ErrorDialog import Ui_ErrorDialog
else:
    Ui_ErrorDialog = ui_utils.load_ui("ErrorDialog")

__all__ = ["ErrorDialog", "get_exc_dialog", "raise_exc_dialog"]


class ErrorDialog(Ui_ErrorDialog, QDialog):

    def __init__(self,
                 exc_type: Type[BaseException] = None,
                 exc_value: BaseException = None,
                 exc_traceback=None):
        super().__init__()
        self.setupUi(self)

        self.buttonDetails.clicked.connect(lambda: self.toggle_details())
        self.dialogButtons.clicked.connect(self.reject)
        self.toggle_details(False)

        self.setWindowTitle("Error" if exc_type is None else exc_type.__name__)
        if exc_value is not None:
            self.text = str(exc_value)
        if exc_traceback is not None:
            self.details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

    @property
    def text(self) -> str:
        return self.textMain.toPlainText()

    @text.setter
    def text(self, text: str = None):
        self.textMain.setText(text if text else "")
        self.textMain.verticalScrollBar().setValue(self.textMain.verticalScrollBar().maximum())

    @property
    def details(self) -> str:
        return self.textDetails.toPlainText()

    @details.setter
    def details(self, text: str = None):
        if not text:
            self.toggle_details(False)
            self.buttonDetails.hide()
        self.textDetails.setText(text if text else "")
        self.textDetails.verticalScrollBar().setValue(self.textDetails.verticalScrollBar().maximum())

    def toggle_details(self, expand: bool = None):
        if expand is None:
            expand = self.groupDetails.isHidden()
        self.buttonDetails.setText(f"{self.tr('details')} {'-' if expand else '+'}")
        self.groupDetails.setHidden(not expand)
        self.textDetails.verticalScrollBar().setValue(self.textDetails.verticalScrollBar().maximum())
        self.adjustSize()


def get_exc_dialog() -> ErrorDialog:
    d = ErrorDialog(*sys.exc_info())
    d.setModal(True)
    return d


def raise_exc_dialog():
    return get_exc_dialog().exec_()
