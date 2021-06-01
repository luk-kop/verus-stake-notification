#!/usr/bin/env python3
import os

from dotenv import load_dotenv, set_key

from aws_resources import SnsTopic, IamRoleLambda, LambdaFunction, ApiGateway


class VerusStakeNotification:
    """
    Class represents all AWS resources necessary to run Verus notification project.
    """
    def __init__(self, email: str):
        # Deploy SNS topic
        self.topic = SnsTopic(name='verus-topic')
        self.topic.subscribe_endpoint(endpoint=email)
        # Deploy IAM Role for Lambda
        self.iam_role = IamRoleLambda(name='verus-lambda-to-sns',
                                      topic_arn=self.topic.arn)
        # Deploy Lambda function
        self.lambda_function = LambdaFunction(name='verus-lambda-func',
                                              role_arn=self.iam_role.arn,
                                              topic_arn=self.topic.arn)
        # Deploy API Gateway
        self.api = ApiGateway(name='verus-api-gateway', lambda_arn=self.lambda_function.arn)
        # Grants API Gateway permission to use Lambda function
        self.lambda_function.add_permission(source_arn=self.api.source_arn)
        self.url = self.api.url

    def delete(self) -> None:
        """
        Destroy all AWS resources.
        """
        self.topic.delete_topic()
        self.lambda_function.delete_function()
        self.api.delete_api()
        self.iam_role.delete_role()


if __name__ == '__main__':
    # Get environment variables from .env file
    load_dotenv()

    EMAIL_TO_NOTIFY = os.getenv('EMAIL_TO_NOTIFY')
    test = VerusStakeNotification(email=EMAIL_TO_NOTIFY)

    # Write API URL to .env file.
    set_key(dotenv_path='.env', key_to_set='NOTIFICATION_API_URL', value_to_set=test.url)

    # test.delete()


