import json
import boto3
import os


def lambda_handler(event, context):
    """
    Publish a message to the SNS topic.
    """
    client = boto3.client('sns')
    response = client.publish(
        TopicArn=os.environ.get('TOPIC_ARN'),
        Message='New stake in your VRSC wallet',
        Subject='New stake',
    )

    return {
        'statusCode': 200,
        'body': json.dumps('Notification sent!')
    }