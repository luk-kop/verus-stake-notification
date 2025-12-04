import argparse
import os
import subprocess
import json
import sys

from dotenv import load_dotenv

from utils import EnvApiFile, TerraformBackendBlock, get_path


def store_terraform_output() -> None:
    """
    Function store necessary data from terraform output to .env-api file.
    Stored data will be used with API call.
    """
    try:
        terraform_output_data_json = subprocess.getoutput("terraform output -json")
        terraform_output_data: dict = json.loads(terraform_output_data_json)
        cognito_scopes_list: list = terraform_output_data["cognito_scopes"]["value"]
        # Initialize .env-api file
        env_api_file = EnvApiFile(
            notification_api_url=terraform_output_data["api_url"]["value"],
            cognito_client_id=terraform_output_data["cognito_client_id"]["value"],
            cognito_client_secret=terraform_output_data["cognito_client_secret"][
                "value"
            ],
            cognito_token_url=terraform_output_data["cognito_token_url"]["value"],
            cognito_custom_scopes=cognito_scopes_list,
        )
    except (json.decoder.JSONDecodeError, KeyError, AttributeError):
        print("Issue with terraform output. Exiting the script...")
        sys.exit()
    # Write terraform output data to .env-api file.
    print("Store terraform output data to .env-api file")
    env_api_file.store()


def build_resources_wrapper(command_params: dict) -> None:
    """
    Function run by the parser to build AWS resources.
    """
    # Check whether '.terraform' dir exist - if not initialize Terraform working directory
    if not get_path(name="terraform/.terraform", directory=True):
        init_terraform_wrapper()
    aws_region = command_params["region"]
    aws_profile = command_params["profile"]
    # Get SNS Topic subscription email from env var
    email_to_notify = os.getenv("EMAIL_TO_NOTIFY")
    wallet_ip = os.getenv("WALLET_PUBLIC_IP")
    options = [
        "terraform",
        "apply",
        f"-var=region={aws_region}",
        f"-var=profile={aws_profile}",
        f"-var=sns_email={email_to_notify}",
    ]
    if wallet_ip:
        options.append(f"-var=wallet_ip={wallet_ip}")
    # Run 'terraform apply'
    subprocess.run(args=options)
    # Run 'terraform output api_url' to get necessary data for API call
    store_terraform_output()


def destroy_resources_wrapper() -> None:
    """
    Function run by the parser to remove AWS resources.
    """
    options = ["terraform", "destroy"]
    # Run 'terraform destroy'
    subprocess.run(args=options)
    # Clear .env-api file
    print("Clearing data in .env-api file...")
    EnvApiFile().store()


def plan_resources_wrapper(command_params: dict) -> None:
    """
    Function run by the parser to plan AWS resources.
    """
    # Check whether '.terraform' dir exist - if not initialize Terraform working directory
    if not get_path(name="terraform/.terraform", directory=True):
        init_terraform_wrapper()
    aws_region = command_params["region"]
    aws_profile = command_params["profile"]
    # Get SNS Topic subscription email from env var
    email_to_notify = os.getenv("EMAIL_TO_NOTIFY")
    wallet_ip = os.getenv("WALLET_PUBLIC_IP")
    options = [
        "terraform",
        "plan",
        f"-var=region={aws_region}",
        f"-var=profile={aws_profile}",
        f"-var=sns_email={email_to_notify}",
    ]
    if wallet_ip:
        options.append(f"-var=wallet_ip={wallet_ip}")
    # Run 'terraform plan'
    subprocess.run(args=options)


def init_terraform_wrapper() -> None:
    """
    Function run by the parser to initialize Terraform working directory.
    """
    tf_backend_filename = "config.s3.tfbackend"
    backend_handler = TerraformBackendBlock(
        terraform_dir=".", tf_backend_filename=tf_backend_filename
    )

    # Setup backend based on config file existence
    backend_handler.setup_backend()

    # Initialize terraform
    if backend_handler._backend_config_exists():
        print("🚀 Initializing Terraform with S3 backend...")
        options = ["terraform", "init", f"-backend-config={tf_backend_filename}"]
    else:
        print("🚀 Initializing Terraform with local backend...")
        options = ["terraform", "init"]

    subprocess.run(args=options)


if __name__ == "__main__":
    env_file = ".env"
    env_path = get_path(name=env_file, directory=False)
    if not env_path:
        print(f"File {env_file} not exists!")
        sys.exit(1)
    # Get environment variables from .env file
    load_dotenv(env_path)
    # Create parent parser
    parser_parent = argparse.ArgumentParser(
        description="The script deploys AWS resources with terraform"
    )
    # Add arguments
    parser_parent.add_argument(
        "--region",
        default="eu-west-1",
        type=str,
        help="AWS region in which resources will be deployed (default: eu-west-1)",
    )
    parser_parent.add_argument(
        "--profile",
        default="default",
        type=str,
        help="AWS profile used to deploy resources (default: default)",
    )
    # Add subparsers
    subparsers = parser_parent.add_subparsers(title="Valid actions", dest="action")
    # Create parser for 'init' command
    parser_init = subparsers.add_parser(
        name="init", help="Initialize Terraform working directory"
    )
    parser_init.set_defaults(func=init_terraform_wrapper)
    # Create parser for 'plan' command
    parser_plan = subparsers.add_parser(name="plan", help="Plan AWS environment")
    parser_plan.set_defaults(func=plan_resources_wrapper)
    # Create parser for 'build' command
    parser_build = subparsers.add_parser(name="build", help="Build AWS environment")
    parser_build.set_defaults(func=build_resources_wrapper)
    # Create parser for 'destroy' command
    parser_destroy = subparsers.add_parser(
        name="destroy", help="Remove already created AWS environment"
    )
    parser_destroy.set_defaults(func=destroy_resources_wrapper)

    args = parser_parent.parse_args()

    # Change dir to 'terraform'
    os.chdir("terraform")

    if args.action in ["build", "plan"]:
        func_params = {"region": args.region, "profile": args.profile}
        # Call selected action
        args.func(func_params)
    elif args.action == "destroy":
        # Call selected action
        args.func()
    elif args.action == "init":
        # Call selected action
        args.func()
    else:
        # If no attribute is given, print help
        parser_parent.print_help()
