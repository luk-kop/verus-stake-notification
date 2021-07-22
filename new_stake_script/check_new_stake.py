import psutil
import subprocess
import json
from typing import Union
import sys
from pathlib import Path
import logging

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
                return
            self._store_txcount()
            if self._is_immature_balance():
                # Load API related env vars from .env-api file.
                env_data = self._load_env_data()
                # Trigger external API
                api = ApiGatewayCognito(env_data=env_data)
                api.call()
                logger.info('New stake')
                return
        logger.error('verusd process is not running')

    def _load_env_data(self) -> Union[None, dict]:
        """
        Load API environment variables from .env-api
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

    def _create_history_file(self) -> None:
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

    def call(self) -> None:
        """
        Method triggers the API Gateway endpoint with access token as the value of the Authorization header.
        """
        access_token = self.get_access_token()
        headers = {
            'Authorization': access_token
        }
        response = requests.get(self.api_gateway_url, headers=headers)
        self.check_response_status(response)

    def get_access_token(self) -> str:
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
        response = requests.post(
            url=self.cognito_token_url,
            data=body,
            auth=(self.cognito_client_id, self.cognito_client_secret),
            headers=headers
        )
        self.check_response_status(response)
        return response.json()['access_token']

    def check_response_status(self, response) -> None:
        """
        Exit script when response status code different than 200.
        """
        if response.status_code != 200:
            response_text = (response.text[:87] + '...') if len(response.text) > 90 else response.text
            logger.error(f'API response: {response.code} {response_text}')
            sys.exit()


if __name__ == '__main__':
    verus_check = VerusStakeChecker()
    verus_check.run()
