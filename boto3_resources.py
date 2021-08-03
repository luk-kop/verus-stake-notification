import os
import argparse

from dotenv import load_dotenv, set_key

from resources.aws_resources import SnsTopic, IamRoleLambda, LambdaFunction, DynamoDb
from resources.aws_api_gateway import ApiResources
from resources.aws_cognito import CognitoResources
from terraform_resources import get_env_path


class VerusStakeNotification:
    """
    Class represents all AWS resources necessary to run Verus stake notification project.
    """
    def __init__(self) -> None:
        # Deploy SNS topic
        self.topic = SnsTopic(name='vrsc-topic-boto3')
        # Deploy DynamoDB
        self.dynamodb = DynamoDb(name='vrsc-stakes-db-boto3')
        # Deploy IAM Role for Lambda
        self.iam_role = IamRoleLambda(name='vrsc-lambda-to-sns-boto3',
                                      topic_arn=self.topic.arn,
                                      dynamodb_arn=self.dynamodb.arn)
        # Deploy Lambda function
        self.lambda_function = LambdaFunction(name='vrsc-lambda-func-boto3',
                                              role_arn=self.iam_role.arn,
                                              topic_arn=self.topic.arn,
                                              dynamodb_table_name=self.dynamodb.name)
        # Deploy Cognito
        scopes = [
            {
                'name': 'api-read',
                'description': 'Read access to the API'
            }
        ]
        self.cognito = CognitoResources(user_pool_name='vrsc-notification-pool-boto3',
                                        resource_server_scopes=scopes,
                                        pool_domain='vrsc-creds-boto3',
                                        name_prefix='vrsc')
        # Deploy API Gateway
        self.api = ApiResources(api_name='vrsc-api-gateway-boto3',
                                lambda_arn=self.lambda_function.arn,
                                http_methods=['GET'],
                                stage_name='vrsc',
                                user_pool=self.cognito.user_pool)
        # Grants API Gateway permission to use Lambda function
        self.lambda_function.add_permission(source_arn=self.api.arn)
        self.url = self.api.invoke_url
        self.cognito_client_credentials = self.cognito.client_credentials
        self.cognito_token_url = self.cognito.token_url
        self.scopes_list = self.cognito.scopes_list

    def subscribe_email(self, email: str) -> None:
        """
        Subscribe email (endpoint) to SNS topic.
        """
        self.topic.subscribe_endpoint(endpoint=email)

    def destroy(self) -> None:
        """
        Destroy (delete) all AWS resources related to Verus stake notification project.
        """
        self.topic.delete_topic()
        self.dynamodb.delete_table()
        self.lambda_function.delete_function()
        self.api.delete()
        self.cognito.delete()
        self.iam_role.delete_role()


def build_resources_wrapper() -> None:
    """
    Function run by the parser to build AWS resources.
    """
    email_to_notify = os.getenv('EMAIL_TO_NOTIFY')
    verus_resources = VerusStakeNotification()
    verus_resources.subscribe_email(email=email_to_notify)

    data_to_store = {
        'NOTIFICATION_API_URL': verus_resources.url,
        'COGNITO_CLIENT_ID': verus_resources.cognito_client_credentials['client_id'],
        'COGNITO_CLIENT_SECRET': verus_resources.cognito_client_credentials['client_secret'],
        'COGNITO_TOKEN_URL': verus_resources.cognito_token_url,
        'COGNITO_OAUTH_LIST_OF_SCOPES': verus_resources.scopes_list
    }
    # Write relevant resource data to .env-api file.
    print('Store resources data to .env-api file')
    for data_key, data_value in data_to_store.items():
        set_key(dotenv_path='new_stake_script/.env-api', key_to_set=data_key, value_to_set=data_value)


def destroy_resources_wrapper() -> None:
    """
    Function run by the parser to remove AWS resources.
    """
    verus_resources = VerusStakeNotification()
    verus_resources.destroy()


if __name__ == '__main__':
    env_path = get_env_path()
    # Get environment variables from .env file
    load_dotenv(env_path)
    # Create parser
    parser = argparse.ArgumentParser(
        description='The script deploys/removes AWS resources for verus-stake-notification project'
    )

    subparsers = parser.add_subparsers(title='Valid actions')
    # Create parser for 'build' command
    parser_build = subparsers.add_parser('build', help='Build AWS environment')
    parser_build.set_defaults(func=build_resources_wrapper)
    # Create parser for 'destroy' command
    parser_destroy = subparsers.add_parser('destroy', help='Remove already created AWS environment')
    parser_destroy.set_defaults(func=destroy_resources_wrapper)
    args = parser.parse_args()
    try:
        # Call selected action
        args.func()
    except AttributeError:
        # if no attribute is given, print help
        parser.print_help()



