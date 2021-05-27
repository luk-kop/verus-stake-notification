#!/usr/bin/env python3
import boto3
from typing import Union


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
                        'Value': 'Verus-notification'
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


if __name__ == '__main__':
    topic_test = SnsTopic(name='test123')
