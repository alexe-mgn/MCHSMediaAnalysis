import traceback
import os
import sys
import subprocess

import utils


def install():
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", utils.PATH.LOAD])
    import spacy.cli
    spacy.cli.download("ru_core_news_sm")
    import plotly.offline
    with open(os.path.join(utils.PATH.PLOTLY_JS), mode='w') as f:
        f.write(plotly.offline.get_plotlyjs())


if __name__ == "__main__":
    try:
        install()
    except BaseException:
        traceback.print_exc()
    input("Press enter to exit\n")
