from typing import *

import locale
import datetime
import calendar

old_loc = locale.getlocale(locale.LC_TIME)
locale.setlocale(locale.LC_TIME, 'ru')
_month_pref = [e.lower()[:-1] for e in calendar.month_name]
locale.setlocale(locale.LC_TIME, old_loc)


class Timezone(datetime.tzinfo):

    def __init__(self, utc_offset: int = 0):
        self._utc_offset = utc_offset

    def utcoffset(self, dt: Optional[datetime.datetime]) -> Optional[datetime.timedelta]:
        return datetime.timedelta(hours=self._utc_offset)

    def dst(self, dt: Optional[datetime.datetime]) -> Optional[datetime.timedelta]:
        return datetime.timedelta()


def month_to_int(name: str):
    for n, i in enumerate(_month_pref):
        if name.lower().startswith(i):
            return n
