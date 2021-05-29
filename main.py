#!/usr/bin/env python3
import json
from typing import Union, List

import boto3
from botocore.exceptions import ClientError


class SnsTopic:
    """
    Class represents SNS Topic resource.
    """
    def __init__(self, name: str):
        self.name = name
        self.sns_client = boto3.client('sns')
        self.arn = None
        # Create Topic if not already exist
        self.create_topic()

    @property
    def subscriptions(self) -> list:
        """
        Returns a list of subscriptions to a specific topic.
        """
        return self.sns_client.list_subscriptions_by_topic(TopicArn=self.arn)['Subscriptions']

    def create_topic(self) -> None:
        """
        Creates SNS Topic resource. Method is called whenever a new instance of SnsTopic is created.
        Method can also be used to recreate SNS Topic resource after deleting it with 'delete_topic' method.
        """
        if not self.check_topic_exist():
            topic = self.sns_client.create_topic(
                Name=self.name,
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    }
                ]
            )
            self.arn = topic['TopicArn']
            print(f'The topic {self.name} created')

    def check_topic_exist(self) -> bool:
        """
        Checks whether a topic with the given name already exists.
        If topic already exists - assign existed topic ARN to 'arn' attribute.
        """
        topics = self.sns_client.list_topics()['Topics']
        for topic in topics:
            topic_arn = topic.get('TopicArn')
            if topic_arn and topic_arn.split(':')[-1] == self.name:
                print(f'Topic {self.name} exist. Using it.')
                self.arn = topic_arn
                return True
        return False

    def subscribe_endpoint(self, endpoint: str, protocol: str = 'email') -> None:
        """
        Adds subscription to topic
        """
        sub_arn = self.check_subscription_exist(endpoint)
        if sub_arn:
            print(f'The subscription {endpoint} already exist')
        else:
            self.sns_client.subscribe(
                TopicArn=self.arn,
                Protocol=protocol,
                Endpoint=endpoint,
                ReturnSubscriptionArn=False
            )
            print(f'The subscription {endpoint} added to {self.name} topic')

    def unsubscribe_endpoint(self, endpoint: str) -> None:
        """
        Deletes specific subscription.
        """
        sub_arn = self.check_subscription_exist(endpoint)
        if sub_arn:
            if sub_arn == 'PendingConfirmation':
                print(f'The subscription "{endpoint}" can\'t be deleted (\'Pending confirmation\' status)')
                return
            else:
                self.sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'The subscription {endpoint} has been deleted')
                return
        print(f'The "{endpoint}" is not valid subscription to {self.name} topic')

    def unsubscribe_all_endpoints(self) -> None:
        """
        Deletes all subscriptions.
        """
        for sub in self.subscriptions:
            sub_arn = sub['SubscriptionArn']
            sub_endpoint = sub['Endpoint']
            if sub_arn == 'PendingConfirmation':
                print(f'The subscription "{sub_endpoint}" can\'t be deleted (\'Pending confirmation\' status)')
            else:
                self.sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'The subscription "{sub_endpoint}" has been deleted')

    def check_subscription_exist(self, endpoint: str) -> Union[None, str]:
        """
        Returns subscription ARN if subscription already exist.
        """
        for sub in self.subscriptions:
            sub_endpoint = sub['Endpoint']
            if sub_endpoint == endpoint:
                return sub['SubscriptionArn']

    def delete_topic(self) -> None:
        """
        Deletes topic.
        """
        self.sns_client.delete_topic(TopicArn=self.arn)
        self.arn = None
        print(f'The topic {self.name} has been deleted')


class IamRoleLambda:
    """
    Class represents IAM role resource. If a role with the specified name already exists, it is used.
    IAM role that allow Lambda function to publish messages to a SNS Topic.
    """
    def __init__(self, name: str, topic_arn: str):
        self.name = name
        self.topic_arn = topic_arn
        self.iam_client = boto3.client('iam')
        self.arn = None
        self.role_id = None
        self.create_role()

    def create_role(self) -> None:
        """
        Creates new IAM Role.
        If IAM Role already exists - assign existed IAM Role to 'arn' and 'role_id' attributes.
        """
        try:
            iam_role = self.iam_client.create_role(
                RoleName=self.name,
                AssumeRolePolicyDocument=json.dumps(self.trust_relationship_policy),
                Path='/service-role/',
                Description='IAM role for verus notification',
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    },
                ]
            )
            # Attach AWSLambdaBasicExecutionRole managed policy
            self.iam_client.attach_role_policy(
                RoleName=self.name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
            # Attach inline policy - allow Lambda publish to specified SNS topic
            self.iam_client.put_role_policy(
                RoleName=self.name,
                PolicyName='verus-lambda-sns-publish',
                PolicyDocument=f'{{"Version":"2012-10-17","Statement":'
                               f'{{"Effect":"Allow","Action":"sns:Publish","Resource":"{self.topic_arn}"}}}}'
            )
            print(f'The IAM role {self.name} created')
        except ClientError as error:
            if error.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f'The IMA role {self.name} already exists')
                iam_role = self.iam_client.get_role(RoleName=self.name)
            else:
                print('Unexpected error occurred. Role could not be created', error)
                return
        self.arn = iam_role['Role']['Arn']
        self.role_id = iam_role['Role']['RoleId']

    @property
    def trust_relationship_policy(self) -> dict:
        """
        The trust relationship policy document that grants an entity permission to assume the IAM Role.
        Only Lambda resource can assume this IAM Role.
        """
        policy = {
            'Version': '2012-10-17',
            'Statement': [
                {
                    'Effect': 'Allow',
                    'Principal': {
                        'Service': 'lambda.amazonaws.com'
                    },
                    'Action': 'sts:AssumeRole'
                }
            ]
        }
        return policy

    def list_attached_polices(self) -> List[dict]:
        """
        Lists all managed policies that are attached to the IAM role.
        """
        polices = self.iam_client.list_attached_role_policies(RoleName=self.name)
        return polices.get('AttachedPolicies')

    def attach_policy(self, policy_arn):
        """
        Add the specified managed policy to IAM role.
        """
        self.iam_client.attach_role_policy(
            RoleName=self.name,
            PolicyArn=policy_arn
        )

    def detach_policy(self, policy_arn: str) -> None:
        """
        Removes the specified managed policy from the IAM role.
        """
        self.iam_client.detach_role_policy(
            RoleName=self.name,
            PolicyArn=policy_arn
        )

    def delete_role(self) -> None:
        """
        Deletes the IAM role.
        """
        # Detach all managed policies
        for policy in self.list_attached_polices():
            self.detach_policy(policy['PolicyArn'])
        # Delete IAM Role
        self.iam_client.delete_role(RoleName=self.name)
        print(f'The IAM Role {self.name} has been deleted')


class CustomerIamPolicy:
    """
    Class represents customer managed IAM policy.
    Policy is NOT deployed when a new CustomerIamPolicy instance is created.
    To deploy policy to AWS use 'create_policy' method on CustomerIamPolicy object.
    """
    def __init__(self, name):
        self.name = name
        self.arn = None
        self.iam_client = boto3.client('iam')
        self.statement = []

    def add_policy_to_statement(self, effect: str, actions: list, resource: str) -> None:
        """
        Adds policies details to 'Statement' part.
        """
        policy = {
            'Effect': effect,
            'Action': actions[0] if len(actions) == 1 else actions,
            'Resource': resource
        }
        self.statement.append(policy)

    def check_policy_exist(self) -> bool:
        """
        Returns policy ARN if policy already exist in 'Local' scope.
        """
        local_policies = self.iam_client.list_policies(Scope='Local')['Policies']
        for policy in local_policies:
            if policy['PolicyName'] == self.name:
                print(f'The policy {self.name} already exists. Using it.')
                self.arn = policy['Arn']
                return True
        return False

    def create_policy(self) -> None:
        """
        Creates customer managed policy - if not exists.
        """
        policy_arn = self.check_policy_exist()
        if not policy_arn:
            policy = {
                'Version': '2012-10-17',
                'Statement': self.statement
            }
            iam_policy = self.iam_client.create_policy(
                PolicyName=self.name,
                PolicyDocument=json.dumps(policy),
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    },
                ]
            )
            self.arn = iam_policy['Policy']['Arn']
            print(f'Policy {self.name} created')

    def delete_policy(self) -> None:
        """
        Deletes customer managed policy.
        """
        if self.arn:
            self.iam_client.delete_policy(PolicyArn=self.arn)
            print(f'The policy {self.name} has been deleted')


def create_resources():
    # Deploy SNS topic
    topic_test = SnsTopic(name='test123')
    # Deploy IAM Role for Lambda
    iam_role = IamRoleLambda(name='verus-lambda-to-sns', topic_arn=topic_test.arn)
    # iam_role.delete_role()


def delete_resources():
    pass


if __name__ == '__main__':
    create_resources()

