from typing import *
import datetime
import os

import logging

from sqlalchemy.engine import URL

import utils

if TYPE_CHECKING:
    from .updater import UPDATE_RECORD

__all__ = ["ScheduleFileStore"]


class ScheduleFileStore:
    _separator = '\x00'

    def __init__(self, file: str = None):
        self.file = file

    @staticmethod
    def _parse_edge(dt: str):
        return None if dt.strip().lower() in {'none', '-'} else datetime.datetime.fromisoformat(dt)

    @staticmethod
    def _dump_edge(dt: Optional[datetime.datetime]):
        return "None" if dt is None else dt.isoformat(sep=" ")

    @classmethod
    def _parse_update_record(cls, line: str) -> Optional["UPDATE_RECORD"]:
        args = line.strip('\n').split(cls._separator, 4)
        if len(args) == 5:
            try:
                return datetime.datetime.fromisoformat(args[0]), \
                       cls._parse_edge(args[1]), cls._parse_edge(args[2]), \
                       args[3], args[4]
            except ValueError:
                pass
        return None

    @classmethod
    def _dump_update_record(cls, upd: "UPDATE_RECORD"):
        s = cls._separator
        return f"{upd[0].isoformat(sep=' ')}{s}" \
               f"{cls._dump_edge(upd[1])}{s}{cls._dump_edge(upd[2])}{s}" \
               f"{str(upd[3])}{s}{str(upd[4])}"

    def refresh(self) -> List["UPDATE_RECORD"]:
        schedule = []
        schedule.clear()
        parse_line = self._parse_update_record
        if file := self.file:
            if os.path.isfile(file):
                with open(file, mode='r') as f:
                    for line in f.readlines():
                        if (upd := parse_line(line)) is not None:
                            schedule.append(upd)
                        else:
                            logging.debug(f"Invalid update line in schedule \"{line}\"")
            else:
                logging.debug(f"Update schedule file is not found in {utils.PATH.SCHEDULE} by {self}")
        schedule.sort(key=lambda rec: rec[0])
        return schedule

    def dump(self, schedule: List["UPDATE_RECORD"]):
        dump_line = self._dump_update_record
        with open(self.file, mode='w') as f:
            for upd in sorted(schedule, key=lambda rec: rec[0]):
                f.write(dump_line(upd))
                f.write('\n')
