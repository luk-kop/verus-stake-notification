import argparse
import os
import subprocess
import json
import sys

from dotenv import load_dotenv

from utils import EnvApiFile, TerraformBackendFile, get_env_path


def store_terraform_output() -> None:
    """
    Function store necessary data from terraform output to .env-api file.
    Stored data will be used with API call.
    """
    try:
        terraform_output_data_json = subprocess.getoutput('terraform output -json')
        terraform_output_data: dict = json.loads(terraform_output_data_json)
        cognito_scopes_list: list = terraform_output_data['cognito_scopes']['value']
        # Initialize .env-api file
        env_api_file = EnvApiFile(
            notification_api_url=terraform_output_data['api_url']['value'],
            cognito_client_id=terraform_output_data['cognito_client_id']['value'],
            cognito_client_secret=terraform_output_data['cognito_client_secret']['value'],
            cognito_token_url=terraform_output_data['cognito_token_url']['value'],
            cognito_custom_scopes=cognito_scopes_list
        )
    except (json.decoder.JSONDecodeError, KeyError, AttributeError):
        print('Issue with terraform output. Exiting the script...')
        sys.exit()
    # Write terraform output data to .env-api file.
    print('Store terraform output data to .env-api file')
    env_api_file.store()


def build_resources_wrapper(command_params: dict) -> None:
    """
    Function run by the parser to build AWS resources.
    """
    aws_region = command_params['region']
    aws_profile = command_params['profile']
    # Get SNS Topic subscription email from env var
    email_to_notify = os.getenv('EMAIL_TO_NOTIFY')
    wallet_ip = os.getenv('WALLET_PUBLIC_IP')
    options = ['terraform', 'apply', f'-var=region={aws_region}', f'-var=profile={aws_profile}',
               f'-var=sns_email={email_to_notify}']
    if wallet_ip:
        options.append(f'-var=wallet_ip={wallet_ip}')
    # Run 'terraform apply'
    subprocess.run(args=options)
    # Run 'terraform output api_url' to get necessary data for API call
    store_terraform_output()


def destroy_resources_wrapper() -> None:
    """
    Function run by the parser to remove AWS resources.
    """
    options = ['terraform', 'destroy']
    # Run 'terraform destroy'
    subprocess.run(args=options)
    # Clear .env-api file
    print('Clearing data in .env-api file...')
    EnvApiFile().store()


def init_terraform_wrapper() -> None:
    """
    Function run by the parser to initialize Terraform working directory.
    """
    tf_backend_filename = 'backend.hcl'
    tf_backend = TerraformBackendFile(filename=tf_backend_filename)
    if not tf_backend.validate_file():
        sys.exit(1)
    options = ['terraform', 'init', f'-backend-config={tf_backend_filename}']
    # Run 'terraform init -backend-config=backend.hcl'
    print('Initializing Terraform working directory...')
    subprocess.run(args=options)


if __name__ == '__main__':
    env_path = get_env_path()
    # Get environment variables from .env file
    load_dotenv(env_path)
    # Create parent parser
    parser_parent = argparse.ArgumentParser(description='The script deploys AWS resources with terraform')
    # Add arguments
    parser_parent.add_argument('--region', default='eu-west-1', type=str,
                               help='AWS region in which resources will be deployed (default: eu-west-1)')
    parser_parent.add_argument('--profile', default='default', type=str,
                               help='AWS profile used to deploy resources (default: default)')
    # Add subparsers
    subparsers = parser_parent.add_subparsers(title='Valid actions', dest='action')
    # Create parser for 'init' command
    parser_build = subparsers.add_parser(name='init', help='Initialize Terraform working directory')
    parser_build.set_defaults(func=init_terraform_wrapper)
    # Create parser for 'build' command
    parser_build = subparsers.add_parser(name='build', help='Build AWS environment')
    parser_build.set_defaults(func=build_resources_wrapper)
    # Create parser for 'destroy' command
    parser_destroy = subparsers.add_parser(name='destroy', help='Remove already created AWS environment')
    parser_destroy.set_defaults(func=destroy_resources_wrapper)

    args = parser_parent.parse_args()

    # Change dir to 'terraform_files'
    os.chdir('terraform_files')

    if args.action == 'build':
        func_params = {
            'region': args.region,
            'profile': args.profile
        }
        # Call selected action
        args.func(func_params)
    elif args.action == 'destroy':
        # Call selected action
        args.func()
    elif args.action == 'init':
        # Call selected action
        args.func()
    else:
        # if no attribute is given, print help
        parser_parent.print_help()
