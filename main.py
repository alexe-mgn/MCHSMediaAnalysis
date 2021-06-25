import sys


def excepthook(exc_type, exc_value, exc_traceback):
    sys.__excepthook__(exc_type, exc_value, exc_traceback)

    from ui.error_dialog import ErrorDialog

    d = ErrorDialog(exc_type, exc_value, exc_traceback)
    d.setModal(True)
    d.exec_()


sys.excepthook = excepthook

if __name__ == "__main__":
    from ui.ui_utils import update_all_ui_once

    update_all_ui_once()

    from ui import run_app

    run_app()
