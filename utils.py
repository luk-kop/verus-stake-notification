from dataclasses import dataclass
from typing import Union, Optional, Dict, List
from pathlib import Path, PosixPath

from dotenv import set_key
import hcl2
from lark import exceptions as hcl2_exception


def get_path(name: str, directory: bool = False) -> Optional[PosixPath]:
    """
    Return file/dir path if exists.
    """
    path = Path(__file__).resolve().parent.joinpath(name)
    if path.exists():
        if directory and path.is_dir():
            return path
        elif path.is_file():
            return path


@dataclass
class TerraformBackendConfigFile:
    """
    The class representing Terraform config backend file.
    """

    filename: str

    @property
    def _filename_path(self) -> PosixPath:
        """
        File absolute path.
        """
        return Path(__file__).resolve().parent.joinpath(f"terraform/{self.filename}")

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
        for _, value in content.items():
            if isinstance(value, str) and value.startswith("${"):
                return False
        return True

    @property
    def file_content(self) -> Dict:
        """
        Return HCL file content as python dict object.
        """
        if self.check_exist():
            try:
                with open(self.filename, "r") as file:
                    hcl_dict = hcl2.load(file)
            except hcl2_exception.UnexpectedInput:
                return {"error": True}
            if not self._check_value_syntax(hcl_dict):
                return {"error": True}
            return hcl_dict
        else:
            return {}

    def validate_file(self) -> Optional[Dict]:
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
        elif hcl_file_content.get("error"):
            print(f'Error: not valid data format in "{self.filename}" file')
            return False
        return True


class TerraformBackendBlock:
    """
    The class representing Terraform file containing backend block.
    """

    def __init__(
        self,
        terraform_dir: str = "terraform",
        backend_block_file: str = "backend.tf",
        tf_backend_filename: str = None,
    ) -> None:
        self.terraform_dir = Path(terraform_dir)
        self.backend_file = self.terraform_dir / backend_block_file
        self.tf_backend_filename = tf_backend_filename

    def create_s3_backend_content(self) -> str:
        """
        Create S3 backend configuration content as HCL string
        """
        return """terraform {
  backend "s3" {}
}
"""

    def setup_backend(self):
        """
        Setup backend based on tf_backend_filename existence
        """
        current_has_backend = self.backend_file.exists()
        should_have_backend = self.tf_backend_filename and self._backend_config_exists()

        # Only change backend if configuration differs from current state
        if should_have_backend and not current_has_backend:
            return self.setup_s3_backend_from_config()
        elif not should_have_backend and current_has_backend:
            return self.setup_local_backend()
        else:
            # Backend is already in correct state
            if should_have_backend:
                print("✅ S3 backend already configured")
            else:
                print("✅ Local backend already configured")
            return True

    def _backend_config_exists(self) -> bool:
        """
        Check if backend configuration file exists
        """
        if not self.tf_backend_filename:
            return False
        config_path = self.terraform_dir / self.tf_backend_filename
        return config_path.exists() and config_path.is_file()

    def setup_local_backend(self):
        """
        Setup local backend by removing backend.tf
        """
        print("🔧 Setting up local backend...")

        if self.backend_file.exists():
            self.backend_file.unlink()
            print(f"✅ Removed {self.backend_file}")
            self._clean_terraform_dir()
        else:
            print("✅ No backend.tf file (already using local backend)")

        return True

    def setup_s3_backend_from_config(self):
        """Setup S3 backend by creating backend.tf from config file"""
        print("🔧 Setting up S3 backend from config file...")

        backend_content = self.create_s3_backend_content()
        self.backend_file.write_text(backend_content)
        print(f"✅ Created {self.backend_file}")

        self._clean_terraform_dir()
        return True

    def setup_s3_backend(
        self,
        bucket: str,
        key: str = "terraform.tfstate",
        region: str = "us-east-1",
        dynamodb_table: Optional[str] = None,
    ):
        """Setup S3 backend by creating backend.tf"""
        print("🔧 Setting up S3 backend...")

        backend_content = self.create_s3_backend_content(
            bucket, key, region, dynamodb_table
        )

        self.backend_file.write_text(backend_content)
        print(f"✅ Created {self.backend_file}")

        self._clean_terraform_dir()
        return True

    def _clean_terraform_dir(self):
        """Clean .terraform directory to force reinitialization"""
        terraform_dir = self.terraform_dir / ".terraform"
        if terraform_dir.exists():
            import shutil

            shutil.rmtree(terraform_dir)
            print("✅ Cleaned .terraform directory")

    def show_current_backend(self):
        """Display current backend configuration"""
        if self.backend_file.exists():
            print(f"📍 Current backend configuration ({self.backend_file}):")
            print(self.backend_file.read_text())
        else:
            print("📍 Current backend: local (no backend.tf file)")

    def validate_terraform_files(self):
        """
        Validate that terraform files exist in the directory
        """
        tf_files = list(self.terraform_dir.glob("*.tf"))
        # Exclude backend.tf from this check since we manage it
        tf_files = [f for f in tf_files if f.name != "backend.tf"]

        if not tf_files:
            raise ValueError(f"No .tf files found in {self.terraform_dir}")
        return tf_files


@dataclass
class EnvApiFile:
    """
    The class representing .env-api file.
    """

    filename: str = ".env-api"
    notification_api_url: str = ""
    cognito_client_id: str = ""
    cognito_client_secret: str = ""
    cognito_token_url: str = ""
    cognito_custom_scopes: Union[List, str] = ""

    @property
    def _filename_path(self) -> PosixPath:
        """
        File absolute path.
        """
        return (
            Path(__file__)
            .resolve()
            .parent.joinpath(f"new_stake_script/{self.filename}")
        )

    @property
    def _env_data(self) -> dict:
        """
        Return env data in proper format for storing.
        """
        data_to_store = {
            "NOTIFICATION_API_URL": self.notification_api_url,
            "COGNITO_CLIENT_ID": self.cognito_client_id,
            "COGNITO_CLIENT_SECRET": self.cognito_client_secret,
            "COGNITO_TOKEN_URL": self.cognito_token_url,
        }
        # A space-separated list of scopes to request for the generated access token
        if len(self.cognito_custom_scopes) == 1:
            data_to_store["COGNITO_CUSTOM_SCOPES"] = self.cognito_custom_scopes[0]
        else:
            data_to_store["COGNITO_CUSTOM_SCOPES"] = " ".join(
                self.cognito_custom_scopes
            )
        return data_to_store

    def store(self) -> None:
        """
        Store env data to .env-api file.
        """
        for data_key, data_value in self._env_data.items():
            set_key(
                dotenv_path=self._filename_path,
                key_to_set=data_key,
                value_to_set=data_value,
            )

    def clear(self) -> None:
        """
        Clear env data in .env-api file.
        """
        self.notification_api_url = ""
        self.cognito_client_id = ""
        self.cognito_client_secret = ""
        self.cognito_token_url = ""
        self.cognito_custom_scopes = ""
