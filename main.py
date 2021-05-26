#!/usr/bin/env python3
import boto3


class SnsTopic:
    def __init__(self, name: str):
        self.name = name
        self.sns_client = boto3.client('sns')
        self.sns_resource = boto3.resource('sns')
        self.arn = None
        # Create Topic if not exist
        self.create_topic()

    @property
    def topic(self):
        """
        Returns topic object.
        """
        if self.arn:
            return self.sns_resource.Topic(self.arn)
        return None

    @property
    def subscriptions(self) -> list:
        """
        Returns a list of subscriptions to a specific topic.
        """
        return self.sns_client.list_subscriptions_by_topic(TopicArn=self.arn)['Subscriptions']

    def create_topic(self):
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

    def check_topic_exist(self):
        """
        Checks whether a topic with the given name already exists.
        """
        topics = self.sns_client.list_topics()['Topics']
        for topic in topics:
            topic_arn = topic.get('TopicArn')
            if topic_arn and topic_arn.split(':')[-1] == self.name:
                self.arn = topic_arn
                return True
        return False

    def subscribe_endpoint(self, endpoint: str, protocol: str = 'email'):
        """
        Add subscription to topic
        """
        self.sns_client.subscribe(
            TopicArn=self.arn,
            Protocol=protocol,
            Endpoint=endpoint,
            ReturnSubscriptionArn=False
        )

    def unsubscribe_endpoint(self, endpoint: str):
        """
        Delete specific subscription.
        """
        for sub in self.subscriptions:
            sub_endpoint = sub['Endpoint']
            if sub_endpoint == endpoint:
                sub_arn = sub['SubscriptionArn']
                self.sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'Subscription {endpoint} has been deleted')
                return
        print(f'The "{endpoint}" is not valid subscription to {self.name} topic')

    def unsubscribe_all_endpoints(self):
        """
        Delete all subscriptions.
        """
        for sub in self.subscriptions:
            sub_arn = sub['SubscriptionArn']
            sub_endpoint = sub['Endpoint']
            if sub['SubscriptionArn'] == 'PendingConfirmation':
                print(f'Subscription "{sub_endpoint}" can\'t be deleted (\'Pending confirmation\' status)')
            else:
                self.sns_client.unsubscribe(SubscriptionArn=sub_arn)
                print(f'Subscription "{sub_endpoint}" has been deleted')

    def delete_topic(self):
        """
        Delete topic.
        """
        self.sns_client.delete_topic(TopicArn=self.arn)


if __name__ == '__main__':

    topic = SnsTopic(name='test2')






