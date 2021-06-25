import traceback
import os
import sys
import subprocess

import utils


def install():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r",
                           os.path.join(utils.PATH.LOAD, "requirements.txt")])

    import spacy.cli
    spacy.cli.download("ru_core_news_sm")

    import ru_core_news_sm
    ru_core_news_sm.load().to_disk(utils.PATH.SPACY_MODEL)

    import plotly.offline
    with open(os.path.join(utils.PATH.PLOTLY_JS), mode='w') as f:
        f.write(plotly.offline.get_plotlyjs())

    import ui
    ui.update_all_ui_once()


if __name__ == "__main__":
    try:
        install()
    except BaseException:
        traceback.print_exc()
    input("Press enter to exit\n")
