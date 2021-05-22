#!/usr/bin/env python3
import psutil
from pathlib import Path
import subprocess
import json
from typing import Union


class VerusProcess:
    """
    The class representing Verus process.
    """
    def __init__(self, name: str = 'verusd') -> None:
        self.name = name

    @property
    def status(self) -> bool:
        return self._check_process_status()

    @property
    def _process(self) -> Union[None, psutil.Process]:
        """
        Return process if exist.
        """
        process_list_by_name = [proc for proc in psutil.process_iter() if proc.name() == self.name]
        if process_list_by_name:
            return process_list_by_name[0]

    @property
    def directory(self) -> str:
        """
        Return process's base directory.
        """
        if self.status:
            return self._process.cwd()
        return ''

    def _check_process_status(self) -> bool:
        """
        Check whether process exist.
        """
        if self._process:
            return True
        return False


class VerusStakeChecker:
    """
    The class responsible for checking to confirm that a new stake has appeared in Verus wallet.
    """
    def __init__(self, script_name: str = 'verus',  txcount_history_file: str = 'txcount_history.txt') -> None:
        self.verus_process = VerusProcess()
        self.script_name = script_name
        self.txcount_history_file = txcount_history_file
        # Create txcount_history.txt if not exist
        if not Path(self.txcount_history_file).is_file():
            open(self.txcount_history_file, 'w').close()

    def run(self) -> None:
        if self.verus_process.status:
            if self._is_txcount_equal():
                # print('Equal')
                return
            self._store_txcount()
            # print('Not equal')
            if self._is_immature_balance():
                # TODO: trigger external API
                # print('New stake')
                pass

    @property
    def txcount_current(self) -> str:
        """
        Return current 'txcount' value.
        """
        wallet_info_dict = self._get_wallet_info()
        return str(wallet_info_dict['txcount'])

    @property
    def txcount_last(self) -> str:
        """
        Return 'txcount' value stored in 'txcount_history_file' (recent value).
        """
        with open(self.txcount_history_file) as file:
            content = file.read()
        return content

    def _get_wallet_info(self) -> dict:
        """
        Get detailed walletinfo from Verus process api.
        """
        verus_script_path = Path(self.verus_process.directory).joinpath(self.script_name)
        options = [verus_script_path, 'getwalletinfo']
        response = subprocess.run(args=options, capture_output=True, text=True)
        return json.loads(response.stdout)

    def _store_txcount(self) -> None:
        """
        Write current 'txcount' value to 'txcount_history_file'.
        """
        with open(self.txcount_history_file, mode='w') as file:
            file.write(self.txcount_current)

    def _get_immature_balance(self) -> int:
        """
        Return current 'immature_balance' value.
        """
        wallet_info_dict = self._get_wallet_info()
        return int(wallet_info_dict['immature_balance'])

    def _is_txcount_equal(self) -> bool:
        """
        Check whether 'txcount' changed.
        """
        return self.txcount_current == self.txcount_last

    def _is_immature_balance(self) -> bool:
        """
        Checks whether the change in 'txcount' value was caused by the new stake.
        If the change was caused by a stake, the 'immature_balance' value (from wallet_info) should be != 0.
        """
        if self._get_immature_balance() == 0:
            return False
        return True


if __name__ == '__main__':
    verus_check = VerusStakeChecker()
    verus_check.run()
