#!/usr/bin/env python3
import psutil


class VerusProcess:
    """
    Class representing Verus process.
    """
    def __init__(self, name: str = 'verusd'):
        self.name = name

    def _check_process_status(self):
        if self._process:
            return True
        return False

    @property
    def _process(self):
        process_list_by_name = [proc for proc in psutil.process_iter() if proc.name() == self.name]
        if process_list_by_name:
            return process_list_by_name[0]

    @property
    def status(self):
        return self._check_process_status()

    @property
    def directory(self):
        if self.status:
            return self._process.cwd()
        return ''


class VerusStakeChecker:
    pass


if __name__ == '__main__':
    verus_process = VerusProcess(name='init')
