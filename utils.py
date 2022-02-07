from dataclasses import dataclass
from typing import Union
from pathlib import Path, PosixPath
import sys

from dotenv import set_key
import hcl2
from lark import exceptions as hcl2_exception


def get_env_path() -> Union[None, PosixPath]:
    """
    Return .env file path if exists.
    """
    path = Path(__file__).resolve().parent.joinpath('.env')
    if not path.exists() or not path.is_file():
        print(f'File {path} not exists!')
        sys.exit()
    return path


@dataclass
class TerraformBackendFile:
    """
    The class representing backend.hcl file.
    """
    filename: str

    @property
    def _filename_path(self) -> PosixPath:
        """
        File absolute path.
        """
        return Path(__file__).resolve().parent.joinpath(f'terraform_files/{self.filename}')

    def check_exist(self) -> bool:
        """
        Checks whether filename exists.
        """
        if not self._filename_path.exists() or not self._filename_path.is_file():
            return False
        return True

    def _check_value_syntax(self, content: dict) -> bool:
        """
        Verify that value syntax is correct - do not allow value in ${}
        """
        for key, value in content.items():
            if isinstance(value, str) and value.startswith('${'):
                return False
        return True

    @property
    def file_content(self) -> dict:
        """
        Return HCL file content as python dict object.
        """
        if self.check_exist():
            try:
                with open(self.filename, 'r') as file:
                    hcl_dict = hcl2.load(file)
            except hcl2_exception.UnexpectedInput:
                return {'error': True}
            if not self._check_value_syntax(hcl_dict):
                return {'error': True}
            return hcl_dict
        else:
            return {}

    def validate_file(self) -> Union[None, dict]:
        """
        Validate HCL file existence and content.
        """
        if not self.check_exist():
            print(f'Error: file "{self.filename}" does not exist')
            return False
        hcl_file_content = self.file_content
        if not hcl_file_content:
            print(f'Error: file "{self.filename}" is empty')
            return False
        elif hcl_file_content.get('error'):
            print(f'Error: not valid data format in "{self.filename}" file')
            return False
        return True


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
    cognito_custom_scopes: Union[list, str] = ''

    @property
    def _filename_path(self) -> PosixPath:
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
        if len(self.cognito_custom_scopes) == 1:
            data_to_store['COGNITO_CUSTOM_SCOPES'] = self.cognito_custom_scopes[0]
        else:
            data_to_store['COGNITO_CUSTOM_SCOPES'] = ' '.join(self.cognito_custom_scopes)
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
        self.cognito_custom_scopes = ''
