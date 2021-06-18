import json
import boto3
import botocore.exceptions
import os
from uuid import uuid4
from datetime import datetime


def put_stake(stake_value: float, db_name):
    """
    Add new stake item to VerusStakes DynamoDB
    """
    if not db_name:
        db_name = 'VerusStakes'
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(db_name)
    # TODO: Try block only for test (dynamodb table does not exist)
    try:
        response = table.put_item(
            Item={
                'stake_id': uuid4().hex,
                'stake_value:': stake_value,
                'stake_ts': datetime.utcnow().isoformat()
            }
        )
    except botocore.exceptions.ClientError as error:
        print(error)


def publish_to_sns(topic_arn: str):
    """
    Publish a message to the SNS topic.
    """
    client = boto3.client('sns')
    response = client.publish(
        TopicArn=topic_arn,
        Message='New stake in your VRSC wallet',
        Subject='New stake',
    )


def lambda_handler(event, context):
    """
    Main function.
    """
    # Publish msg to SNS topic
    publish_to_sns(topic_arn=os.environ.get('TOPIC_ARN'))

    # Current stake value
    stake_value = 12
    # Put stake into DynamoDB
    put_stake(stake_value=stake_value, db_name=os.environ.get('DYNAMODB_NAME'))

    return {
        'statusCode': 200,
        'body': json.dumps('Notification sent!')
    }
