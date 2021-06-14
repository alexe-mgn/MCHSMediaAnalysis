from .ui_utils import update_all_ui_once


def run_app():
    from PyQt5.QtWidgets import QApplication
    from .main_window import MainWindow

    if not (app := QApplication.instance()):
        app = QApplication([])
    mw = MainWindow()
    mw.show()
    if not app.startingUp():
        app.exec_()


__all__ = ["update_all_ui_once", "run_app"]
