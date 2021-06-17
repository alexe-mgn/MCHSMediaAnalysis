"""
Date utilities for site parser.
"""
from typing import *

import locale
import datetime
import calendar

old_loc = locale.getlocale(locale.LC_TIME)
locale.setlocale(locale.LC_TIME, 'ru')
_month_pref = [e.lower()[:-1] for e in calendar.month_name[1:]]
locale.setlocale(locale.LC_TIME, old_loc)


class Timezone(datetime.tzinfo):
    """
    Timezone determined by utc offset.
    """

    def __init__(self, utc_offset: int = 0):
        self._utc_offset = utc_offset

    def utcoffset(self, dt: Optional[datetime.datetime]) -> Optional[datetime.timedelta]:
        return datetime.timedelta(hours=self._utc_offset)

    def dst(self, dt: Optional[datetime.datetime]) -> Optional[datetime.timedelta]:
        return datetime.timedelta()


MCHS_TZ = Timezone(3)


def month_to_int(name: str) -> int:
    """
    Convert russian month name to int.
    """
    for n, i in enumerate(_month_pref, 1):
        if name.lower().startswith(i):
            return n
