import sys

import utils
from ui.error_dialog import ErrorDialog


def excepthook(exc_type, exc_value, exc_traceback):
    d = ErrorDialog(exc_type, exc_value, exc_traceback)
    d.setModal(True)
    d.exec_()
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


sys.excepthook = excepthook

if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    from ui.ui_utils import update_all_ui_once

    update_all_ui_once()

    from ui.main_window import MainWindow

    # run_app()
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.connect_tab.role = "admin"
    mw.show()
    app.exec_()
