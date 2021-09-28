import psutil
import subprocess
import json
from typing import Union
import sys
from pathlib import Path
import logging
from dataclasses import dataclass
from datetime import datetime

from dotenv import dotenv_values
import requests

# Custom logger
logger = logging.getLogger(__name__)
log_path = Path(__file__).resolve().parent.joinpath('stake.log')
file_handler = logging.FileHandler(log_path)
log_format = logging.Formatter('%(asctime)s - %(message)s')
file_handler.setFormatter(log_format)
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)


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
    def __init__(self, txcount_history_file_name: str = 'tx_history.json') -> None:
        self.verus_process = VerusProcess()
        self.verus_script_name = 'verus'
        # Transactions (txs) history file is stored in the same dir as this script.
        self.txcount_history_file_path = Path(__file__).resolve().parent.joinpath(txcount_history_file_name)
        self.wallet_info = self._get_wallet_info()
        self.tx_hist_data = self._read_tx_hist_file()
        self.stake_txs = StakeTransactions()

    def run(self) -> None:
        """
        Run stake checker.
        """
        if self.verus_process.status:
            if not self._check_txcount_changed():
                return
            self._update_txcount()
            # Load API related env vars from .env-api file.
            env_data = self._load_env_data()
            # Trigger external API
            api = ApiGatewayCognito(env_data=env_data)
            new_stake_txs = self._get_wallet_new_stake_txs()
            for tx in new_stake_txs:
                data_to_post = {
                    'txid': tx.txid,
                    'time': tx.time,
                    'amount': tx.amount
                }
                api.call(method='post', data=data_to_post)
                tx_timestamp_format = datetime.fromtimestamp(data_to_post['time']).strftime('%Y-%m-%d %H:%M:%SLT')
                logger.info(f'New stake in wallet at {tx_timestamp_format}')
            self._update_stake_txid()
            self._store_new_tx_data()
            return
        logger.error('verusd process is not running')

    def _load_env_data(self) -> Union[None, dict]:
        """
        Load API environment variables from .env-api.
        """
        env_path = Path(__file__).resolve().parent.joinpath('.env-api')
        if not env_path.exists() or not env_path.is_file():
            logger.error(f'File {env_path} not exists!')
            sys.exit()
        env_data = dotenv_values(env_path)
        env_required = [
            'NOTIFICATION_API_URL',
            'COGNITO_CLIENT_ID',
            'COGNITO_CLIENT_SECRET',
            'COGNITO_OAUTH_LIST_OF_SCOPES',
            'COGNITO_TOKEN_URL'
        ]
        for env in env_required:
            if env not in env_data.keys():
                logger.error(f'The {env} in .env-api is missing.')
                sys.exit()
        return env_data

    @property
    def verus_script_path(self) -> str:
        """
        Return verus script absolute path.
        """
        return Path(self.verus_process.directory).joinpath(self.verus_script_name)

    @property
    def _initial_tx_history_file_content(self) -> dict:
        """
        Initial content for tx history file.
        """
        content = {
            'txid_stake_previous': '',
            'txcount_previous': '0'
        }
        return content

    def _update_txcount(self) -> None:
        """
        Update 'txcount' data with current value.
        """
        self.tx_hist_data['txcount_previous'] = self.txcount_current

    def _update_stake_txid(self, txid: str = '') -> None:
        """
        Update 'txid_stake' data with current or most recent value.
        """
        if txid:
            self.tx_hist_data['txid_stake_previous'] = txid
        else:
            # Update 'txid_stake' data with last known stake txid in wallet
            self.tx_hist_data['txid_stake_previous'] = self._last_wallet_stake_txid

    @property
    def txcount_current(self) -> str:
        """
        Return current 'txcount' value.
        """
        return str(self.wallet_info.get('txcount', 0))

    @property
    def txcount_hist(self) -> str:
        """
        Return 'txcount' value stored in tx history file (recent value).
        """
        return self.tx_hist_data.get('txcount_previous', 0)

    @property
    def _txid_stake_hist(self) -> str:
        """
        Return 'txid' of last stake stored in tx history file (recent value).
        """
        return self.tx_hist_data.get('txid_stake_previous', '')

    def _create_tx_history_file(self, content: dict = None) -> None:
        """
        Create tx history file if not exist
        """
        if not content:
            content = self._initial_tx_history_file_content
        with open(self.txcount_history_file_path, 'w') as outfile:
            json.dump(content, outfile)

    def _read_tx_hist_file(self) -> dict:
        """
        Return content of hist file.
        Create new hist file if not exist or file content is invalid.
        """
        initial_content = self._initial_tx_history_file_content
        try:
            with open(self.txcount_history_file_path) as file:
                content = json.load(file)
                if initial_content.keys() == content.keys():
                    return content
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            pass
        self._create_tx_history_file()
        return initial_content

    def _get_wallet_info(self) -> dict:
        """
        Get detailed walletinfo from Verus process api.
        """
        options = [self.verus_script_path, 'getwalletinfo']
        wallet_info = self._process_call(options=options)
        return wallet_info if wallet_info else {}

    def _process_call(self, options: list) -> Union[dict, list, None]:
        """
        Call Verus process api.
        """
        if self.verus_process.status:
            response = subprocess.run(args=options, capture_output=True, text=True)
            return json.loads(response.stdout)

    @property
    def _last_wallet_stake_txid(self) -> str:
        """
        Return last known stake txid in wallet.
        """
        return self.stake_txs.get_last_stake_txid()

    def _get_wallet_stake_txs(self, count: int = 50) -> None:
        """
        Return list of last 'count' stake transactions (txs) in wallet.
        """
        options = [self.verus_script_path, 'listtransactions', '*', str(count)]
        response = self._process_call(options=options)
        txs = response if response else []
        for tx in txs:
            if tx['category'] == 'mint':
                stake_tx = StakeTransaction(
                    txid=tx['txid'],
                    time=tx['time'],
                    amount=tx['amount'],
                    address=tx['address']
                )
                self.stake_txs.add_stake_tx(stake_tx)

    def _get_wallet_new_stake_txs(self) -> list:
        """
        Return list of ONLY new stake transactions (txs) in wallet.
        New txs relative to stored hist stake txid.
        """
        self._get_wallet_stake_txs()
        return self.stake_txs.get_new_stakes_txs(txid_last=self._txid_stake_hist)

    def _store_new_tx_data(self) -> None:
        """
        Store new/updated tx data in tx history file.
        """
        self._create_tx_history_file(content=self.tx_hist_data)

    def _check_txcount_changed(self) -> bool:
        """
        Check whether 'txcount' changed.
        """
        return self.txcount_current != self.txcount_hist


@dataclass
class StakeTransaction:
    """
    The class representing single stake transaction (tx) in wallet.
    """
    txid: str
    time: int
    amount: float
    address: str


class StakeTransactions:
    """
    The class representing collection of StakeTransaction object.
    """
    def __init__(self):
        self.txs = []

    def add_stake_tx(self, tx) -> None:
        """
        Add StakeTransaction to collection.
        """
        if not isinstance(tx, StakeTransaction):
            raise TypeError('Must be StakeTransaction object.')
        self.txs.append(tx)

    @property
    def txs_sorted(self) -> list:
        """
        Return sorted stake txs (newest at the end).
        """
        return sorted(self.txs, key=lambda tx: tx.time)

    @property
    def stakes_txids(self) -> list:
        """
        Return list of sorted stake txids - newest at the end.
        """
        return [tx.txid for tx in self.txs_sorted]

    def get_last_stake_txid(self) -> str:
        """
        Return last known stake txid in wallet.
        """
        try:
            return self.stakes_txids[-1]
        except IndexError:
            return ''

    def get_stake_tx(self, txid: str) -> Union[StakeTransaction, None]:
        """
        Return specified StakeTransaction object if exist.
        """
        for stake_tx in self.txs:
            if stake_tx.txid == txid:
                return stake_tx
        return

    def get_new_stakes_txs(self, txid_last: str) -> list:
        """
        Return sorted list of only newer txs than the 'txid' specified (newest txs at the end).
        """
        tx_last = self.get_stake_tx(txid=txid_last)
        if tx_last:
            return [tx for tx in self.txs_sorted if tx.time > tx_last.time]
        else:
            return []


class ApiGatewayCognito:
    """
    Class responsible for calling external API using the access token fetched from Cognito service.
    """
    def __init__(self, env_data: dict) -> None:
        self.cognito_token_url = env_data['COGNITO_TOKEN_URL']
        self.cognito_client_id = env_data['COGNITO_CLIENT_ID']
        self.cognito_client_secret = env_data['COGNITO_CLIENT_SECRET']
        self.scopes = env_data['COGNITO_OAUTH_LIST_OF_SCOPES']
        self.api_gateway_url = env_data['NOTIFICATION_API_URL']

    def call(self, method: str, data: dict) -> None:
        """
        Method triggers the API Gateway endpoint with access token as the value of the Authorization header.
        """
        self._check_http_method(method=method)
        access_token = self._get_access_token()
        headers = {
            'Authorization': access_token
        }
        try:
            if method.lower() == 'get':
                # data = {'year': '2021', 'month': '11'}
                response = requests.get(self.api_gateway_url, headers=headers, params=data)
                # return response.json()['body']
            else:
                response = requests.post(self.api_gateway_url, headers=headers, json=data)
        except requests.exceptions.RequestException:
            logger.error(f'API call: failed to establish a new connection')
            sys.exit()
        self._check_response_status(response)

    def _check_http_method(self, method: str) -> None:
        """
        Check whether the HTTP method is allowed for API call.
        """
        if method.lower() not in ['post', 'get']:
            logger.error(f'API method: {method} is not allowed HTTP method')
            sys.exit()

    def _get_access_token(self) -> str:
        """
        Method retrieves the access token from Amazon Cognito authorization server.
        """
        body = {
            'grant_type': 'client_credentials',
            'scope': self.scopes
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        try:
            response = requests.post(
                url=self.cognito_token_url,
                data=body,
                auth=(self.cognito_client_id, self.cognito_client_secret),
                headers=headers
            )
        except requests.exceptions.RequestException:
            logger.error(f'API access token: failed to establish a new connection')
            sys.exit()
        self._check_response_status(response)
        return response.json()['access_token']

    def _check_response_status(self, response) -> None:
        """
        Exit script when response status code different than 200.
        """
        if response.status_code != 200:
            response_text = (response.text[:87] + '...') if len(response.text) > 90 else response.text
            logger.error(f'API response: {response.status_code} {response_text}')
            sys.exit()


if __name__ == '__main__':
    verus_check = VerusStakeChecker()

    # Run Verus check
    # verus_check.run()

    # Only for API tests
    env_data = verus_check._load_env_data()
    api = ApiGatewayCognito(env_data)
    data_post = {
        'txid': 'tx02',
        'time': 123480,
        'amount': 12.0
    }

    data_get = [
        {},
        {
            'year': '2021'
        },
        {
            'year': '2021',
            'month': '09'
        }
    ]
    # API POST call
    # api.call(method='post', data=data_post)
    # API GET calls
    # for data in data_get:
    #     api.call(method='get', data=data)