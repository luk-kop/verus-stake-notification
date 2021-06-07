import psutil
from pathlib import Path
import subprocess
import json
from typing import Union
import urllib.request
import os

from dotenv import load_dotenv


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
    def __init__(self, txcount_history_file_name: str = 'txcount_history.txt') -> None:
        self.verus_process = VerusProcess()
        self.verus_script_name = 'verus'
        self.txcount_history_file_path = Path(__file__).resolve().parent.joinpath(txcount_history_file_name)
        self.wallet_info = self._get_wallet_info()
        # Create txcount history file if not exist
        self._create_history_file()

    def run(self) -> None:
        if self.verus_process.status:
            if not self._is_txcount_different():
                # print('Equal')
                return
            self._store_txcount()
            # print('Not equal')
            if self._is_immature_balance():
                load_dotenv()
                api_url = os.getenv('NOTIFICATION_API_URL')
                # Trigger external API
                contents = urllib.request.urlopen(api_url).read()
                # print('New stake')

    def _create_history_file(self):
        """
        Create txcount history file if not exist
        """
        if not self.txcount_history_file_path.is_file():
            with open(self.txcount_history_file_path, 'w') as file:
                file.write('0')

    @property
    def txcount_current(self) -> str:
        """
        Return current 'txcount' value.
        """
        return str(self.wallet_info.get('txcount', 0))

    @property
    def txcount_last(self) -> str:
        """
        Return 'txcount' value stored in 'txcount_history_file' (recent value).
        """
        with open(self.txcount_history_file_path) as file:
            content = file.read()
        return content

    @property
    def verus_script_path(self) -> str:
        """
        Return verus script absolute path.
        """
        return Path(self.verus_process.directory).joinpath(self.verus_script_name)

    def _get_wallet_info(self) -> dict:
        """
        Get detailed walletinfo from Verus process api.
        """
        if self.verus_process.status:
            options = [self.verus_script_path, 'getwalletinfo']
            response = subprocess.run(args=options, capture_output=True, text=True)
            return json.loads(response.stdout)
        else:
            return {}

    def _store_txcount(self) -> None:
        """
        Write current 'txcount' value to 'txcount_history_file'.
        """
        with open(self.txcount_history_file_path, mode='w') as file:
            file.write(self.txcount_current)

    def _get_immature_balance(self) -> int:
        """
        Return current 'immature_balance' value.
        """
        return int(self.wallet_info.get('immature_balance', 0))

    def _is_txcount_different(self) -> bool:
        """
        Check whether 'txcount' changed.
        """
        return self.txcount_current != self.txcount_last

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
