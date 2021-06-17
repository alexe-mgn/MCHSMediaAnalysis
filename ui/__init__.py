from .ui_utils import update_all_ui_once


def run_app():
    from . import app_config
    from .updater import Updater

    u = Updater()
    u.open_analysis()
    if not app_config.APP.startingUp():
        app_config.APP.exec_()


__all__ = ["update_all_ui_once", "run_app"]
