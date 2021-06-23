from .ui_utils import update_all_ui_once


def run_app(background: bool = False):
    from . import app_config
    from .updater import Updater

    app = app_config.get_app()
    u = Updater()
    if not background:
        u.open_analysis()
    if not app.startingUp():
        app.exec_()


__all__ = ["update_all_ui_once", "run_app"]
