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
            print(f'Topic {self.name} created')

    def check_topic_exist(self) -> bool:
        """
        Checks whether a topic with the given name already exists.
        If topic already exists - assign existed topic ARN to 'arn' attribute.
        """
        topics = self.sns_client.list_topics()['Topics']
        for topic in topics:
            topic_arn = topic.get('TopicArn')
            if topic_arn and topic_arn.split(':')[-1] == self.name:
                print(f'Topic {self.name} exist. Returning an existing topic')
                self.arn = topic_arn
                return True
        return False

    def subscribe_endpoint(self, endpoint: str, protocol: str = 'email') -> None:
        """
        Add subscription to topic
        """
        sub_arn = self.check_subscription_exist(endpoint)
        if sub_arn:
            print(f'Subscription {endpoint} already exist')
        else:
            self.sns_client.subscribe(
                TopicArn=self.arn,
                Protocol=protocol,
                Endpoint=endpoint,
                ReturnSubscriptionArn=False
            )
            print(f'Subscription {endpoint} added to {self.name} topic')

    def unsubscribe_endpoint(self, endpoint: str) -> None:
        """
        Delete specific subscription.
        """
        sub_arn = self.check_subscription_exist(endpoint)
        if sub_arn:
            if sub_arn == 'PendingConfirmation':
                print(f'Subscription "{endpoint}" can\'t be deleted (\'Pending confirmation\' status)')
                return
            else:
                self.sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'Subscription {endpoint} has been deleted')
                return
        print(f'The "{endpoint}" is not valid subscription to {self.name} topic')

    def unsubscribe_all_endpoints(self) -> None:
        """
        Delete all subscriptions.
        """
        for sub in self.subscriptions:
            sub_arn = sub['SubscriptionArn']
            sub_endpoint = sub['Endpoint']
            if sub_arn == 'PendingConfirmation':
                print(f'Subscription "{sub_endpoint}" can\'t be deleted (\'Pending confirmation\' status)')
            else:
                self.sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'Subscription "{sub_endpoint}" has been deleted')

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
        Delete topic.
        """
        self.sns_client.delete_topic(TopicArn=self.arn)
        self.arn = None
        print(f'Topic {self.name} has been deleted')


class IamRole:
    """
    Class represents IAM Role resource.
    IAM Role that allow Lambda function to publish messages to a SNS Topic.
    """
    def __init__(self, name: str = 'verus-lambda-to-sns'):
        self.name = name
        self.iam_client = boto3.client('iam')
        self.arn = None
        self.role_id = None
        self.create_role()

    def create_role(self):
        """
        Creates new IAM Role.
        If IAM Role already exists - assign existed IAM Role to 'arn' and 'role_id' attributes.
        """
        try:
            iam_role = self.iam_client.create_role(
                RoleName=self.name,
                AssumeRolePolicyDocument=json.dumps(self.trust_relationship_policy),
                Path='/service-role/',
                Description='IAM Role for verus notification',
                Tags=[
                    {
                        'Key': 'Project',
                        'Value': 'verus-notification'
                    },
                ]
            )
            print(iam_role)
            # Attach AWSLambdaBasicExecutionRole managed policy
            self.iam_client.attach_role_policy(
                RoleName=self.name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole'
            )
        except ClientError as error:
            if error.response['Error']['Code'] == 'EntityAlreadyExists':
                print('Role already exists')
                iam_role = self.iam_client.get_role(RoleName=self.name)
            else:
                print('Unexpected error occurred. Role could not be created', error)
                return
        self.arn = iam_role['Role']['Arn']
        self.role_id = iam_role['Role']['RoleId']

    @property
    def trust_relationship_policy(self):
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
        Lists all managed policies that are attached to the IAM Role.
        """
        polices = self.iam_client.list_attached_role_policies(RoleName=self.name)
        return polices.get('AttachedPolicies')

    def attach_policy(self, policy_arn):
        """
        Add custom policy to IAM Role.
        """
        self.iam_client.attach_role_policy(
            RoleName=self.name,
            PolicyArn=policy_arn
        )

    def detach_policy(self, policy_arn: str) -> None:
        """
        Removes the specified managed policy from the IAM Role.
        """
        self.iam_client.detach_role_policy(
            RoleName=self.name,
            PolicyArn=policy_arn
        )

    def delete_role(self) -> None:
        """
        Deletes the IAM Role.
        """
        # Detach all managed policies
        for policy in self.list_attached_polices():
            self.detach_policy(policy['PolicyArn'])
        # Delete IAM Role
        self.iam_client.delete_role(RoleName=self.name)
        print(f'IAM Role {self.name} has been deleted')


class IamPolicy:
    """
    Class represents IAM policy.
    """
    def __init__(self, name):
        self.name = name
        self.arn = None
        self.policy_id = None
        self.iam_client = boto3.client('iam')
        self.statement = []

    def add_policy(self, effect: str, action, resource):
        policy = {
            'Effect': effect,
            'Action': action,
            'Resource': resource
        }
        self.statement.append(policy)

    def create_policy(self):
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
        self.policy_id = iam_policy['Policy']['PolicyId']


if __name__ == '__main__':
    topic_test = SnsTopic(name='test123')
    iam_role = IamRole()
    sns_publish = IamPolicy('verus-sns-publish')
    sns_publish.add_policy(effect='Allow', action='sns:Publish', resource=topic_test.arn)
    sns_publish.create_policy()
    iam_role.attach_policy(sns_publish.arn)
    # iam_role.delete_role()