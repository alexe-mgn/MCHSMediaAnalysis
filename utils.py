import os
import sys

FROZEN = getattr(sys, 'frozen', False)
LOAD_MEIPASS = True
LOAD_RELATIVE = False


class PATH:
    EXECUTABLE = os.getcwd()
    RELATIVE = '.'
    MEIPASS = getattr(sys, '_MEIPASS', EXECUTABLE)
    ENGINE = os.path.dirname(os.path.abspath(__file__))
    WRITE = EXECUTABLE
    LOAD = RELATIVE if LOAD_RELATIVE else (MEIPASS if LOAD_MEIPASS and FROZEN else EXECUTABLE)
    UI = os.path.join(LOAD, 'ui/UI')
