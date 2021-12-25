from dataclasses import dataclass
from typing import Union
from pathlib import Path
import sys

from dotenv import set_key


def get_env_path() -> Union[None, str]:
    """
    Return .env file path if exists.
    """
    path = Path(__file__).resolve().parent.joinpath('.env')
    if not path.exists() or not path.is_file():
        print(f'File {path} not exists!')
        sys.exit()
    return path


@dataclass
class EnvApiFile:
    """
    The class representing .env-api file.
    """
    filename: str = '.env-api'
    notification_api_url: str = ''
    cognito_client_id: str = ''
    cognito_client_secret: str = ''
    cognito_token_url: str = ''
    cognito_oauth_list_of_scopes: Union[list, str] = ''

    @property
    def _filename_path(self):
        """
        File absolute path.
        """
        return Path(__file__).resolve().parent.joinpath(f'new_stake_script/{self.filename}')

    @property
    def _env_data(self) -> dict:
        """
        Return env data in proper format for storing.
        """
        data_to_store = {
            'NOTIFICATION_API_URL': self.notification_api_url,
            'COGNITO_CLIENT_ID': self.cognito_client_id,
            'COGNITO_CLIENT_SECRET': self.cognito_client_secret,
            'COGNITO_TOKEN_URL': self.cognito_token_url,
        }
        # A space-separated list of scopes to request for the generated access token
        if len(self.cognito_oauth_list_of_scopes) == 1:
            data_to_store['COGNITO_OAUTH_LIST_OF_SCOPES'] = self.cognito_oauth_list_of_scopes[0]
        else:
            data_to_store['COGNITO_OAUTH_LIST_OF_SCOPES'] = ' '.join(self.cognito_oauth_list_of_scopes)
        return data_to_store

    def store(self) -> None:
        """
        Store env data to .env-api file.
        """
        for data_key, data_value in self._env_data.items():
            set_key(dotenv_path=self._filename_path, key_to_set=data_key, value_to_set=data_value)

    def clear(self) -> None:
        """
        Clear env data in .env-api file.
        """
        self.notification_api_url = ''
        self.cognito_client_id = ''
        self.cognito_client_secret = ''
        self.cognito_token_url = ''
        self.cognito_oauth_list_of_scopes = ''