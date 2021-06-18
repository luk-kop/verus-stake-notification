import argparse
import os
import subprocess

from dotenv import load_dotenv, set_key


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
    # Run 'terraform output api_url' to get API Gateway URL
    api_data = subprocess.run(args=['terraform', 'output', 'api_url'], capture_output=True, text=True)
    api_url = api_data.stdout.strip('"').rstrip('\n')
    if api_url.startswith("https://"):
        os.chdir('..')
        # Write API URL to .env file.
        print('Store API URL to .env file')
        set_key(dotenv_path='.env', key_to_set='NOTIFICATION_API_URL', value_to_set=api_url)


def destroy_resources_wrapper() -> None:
    """
    Function run by the parser to remove AWS resources.
    """
    options = ['terraform', 'destroy']
    # Run 'terraform destroy'
    subprocess.run(args=options)


if __name__ == '__main__':
    # Get environment variables from .env file
    load_dotenv()
    # Create parent parser
    parser_parent = argparse.ArgumentParser(description='The script deploys AWS resources with terraform')
    # Add arguments
    parser_parent.add_argument('--region', default='eu-west-1', type=str,
                               help='AWS region in which resources will be deployed (default: eu-west-1)')
    parser_parent.add_argument('--profile', default='default', type=str,
                               help='AWS profile used to deploy resources (default: default)')
    # Add subparsers
    subparsers = parser_parent.add_subparsers(title='Valid actions', dest='action')
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
    else:
        # if no attribute is given, print help
        parser_parent.print_help()