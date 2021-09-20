import json
import boto3
import botocore.exceptions
import os
from datetime import datetime
from decimal import Decimal


def put_stake_txids_db(stake: dict, table_name: str) -> None:
    """
    Add new stake item to specified DynamoDB table (list of individual stake txs).
    """
    dynamodb = boto3.resource('dynamodb')
    stakes_table = dynamodb.Table(table_name)
    try:
        item = {
            'tx_id': stake['txid'],
            'stake_value': Decimal(str(stake['value'])),
            'stake_ts': stake['time']
        }
        stakes_table.put_item(
            Item=item
        )
    except botocore.exceptions.ClientError as error:
        print(error)


def put_stake_values_db(table_name: str, stake: dict, timestamp: str) -> None:
    """
    Add or update stakes value & count for specified timestamp (time period) in DynamoDB table.
    Create new item if not exist.
    """
    # ts_id - timestamp id
    dynamodb = boto3.resource('dynamodb')
    db_table = dynamodb.Table(table_name)

    item_to_update = get_db_item(table_name=table_name, part_key=timestamp)
    if item_to_update:
        # Update item if timestamp id (ts_id) already exist in db
        updated_stake_data = {
            'stakes_value': item_to_update.get('stakes_value', 0) + stake.get('value', 0),
            'stakes_count': item_to_update.get('stakes_count', 0) + 1
        }
        update_db_item(table_name=table_name, part_key=timestamp, updated_data=updated_stake_data)
    else:
        # Put new item if timestamp id (ts_id) not exist in db
        item_new = {
            'ts_id': timestamp,
            'stakes_value': Decimal(str(stake.get('value', 0))),
            'stakes_count': 1
        }
        db_table.put_item(Item=item_new)


def get_db_item(table_name: str, part_key: str) -> dict:
    """
    Get item from specified DynamoDB table.
    If item not exist return {}.
    """
    dynamodb = boto3.resource('dynamodb')
    db_table = dynamodb.Table(table_name)
    try:
        item_data = db_table.get_item(Key={'ts_id': part_key})
        item = item_data.get('Item', {})
    except botocore.exceptions.ClientError as error:
        print(error)
        item = {}
    if item:
        # Convert Decimal to float or int
        item = {key: float(value) for key, value in item.items() if isinstance(value, Decimal)}
    return item


def update_db_item(table_name: str, part_key: str, updated_data: dict) -> None:
    """
    Update DynamoDB item.
    """
    dynamodb = boto3.resource('dynamodb')
    db_table = dynamodb.Table(table_name)

    db_table.update_item(
        Key={
            'ts_id': part_key,
        },
        UpdateExpression='set stakes_value=:v, stakes_count=:c',
        ExpressionAttributeValues={
            ':v': Decimal(str(updated_data['stakes_value'])),
            ':c': Decimal(str(updated_data['stakes_count']))
        },
        ReturnValues='NONE'
    )


def publish_to_sns(topic_arn: str, stake: dict) -> None:
    """
    Publish a message to the SNS topic.
    """
    sns_client = boto3.client('sns')
    stake_value = stake['value']
    sns_client.publish(
        TopicArn=topic_arn,
        Message=f'New stake in your VRSC wallet - {stake_value} VRSC',
        Subject='New stake',
    )


def check_str_is_number(value: str) -> bool:
    """
    Validate that given value is number.
    """
    try:
        float(value)
        return True
    except ValueError:
        return False


def sanitize_query_params(year: str, month: str) -> tuple:
    """
    Returns the query params in required format.
    - year: '' or '1234' (range 0001-9999)
    - month: '' or '01' (range 01-12)
    """
    if check_str_is_number(year) and 0 < int(year) <= 9999:
        year = f'{int(year):04d}'
    else:
        year = ''
    if check_str_is_number(month) and 0 < int(month) < 13:
        month = f'{int(month):02d}'
    else:
        month = ''
    return year, month


def get_timestamp_id(year: bool = True, month: bool = True, date: datetime = datetime.utcnow()) -> str:
    """
    Returns timestamp id (tp_id) in format '2021-01', '2021' or '01'.
    """
    if not year:
        return date.strftime('%m')
    elif not month:
        return date.strftime('%Y')
    return date.strftime('%Y-%m')


def lambda_handler(event, context) -> dict:
    """
    Main function.
    """
    # Load envs
    # Table that contains consolidated stake values for specific timestamp (time period).
    table_values_name = os.environ.get('DYNAMODB_VALUES_NAME')
    # Table that contains list of individual stake transactions (tx) - stake tx id, stake value, stake timestamp.
    table_txid_name = os.environ.get('DYNAMODB_TXIDS_NAME')
    sns_topic_arn = os.environ.get('TOPIC_ARN')

    http_method = event.get('http_method')

    if http_method == 'GET':
        # Get and sanitize query params
        # Valid query params:
        # - year: '' or number in format '1234' (range 0001-9999)
        # - month" '' or number in format '02' (range 01-12)
        qp_year, qp_month = sanitize_query_params(year=event['year'], month=event['month'])

        # Define DynamoDB partition key value
        if qp_year and not qp_month:
            # The stakes value for the whole 'year' will be returned
            part_key = f'{qp_year}'
        elif not qp_year and qp_month:
            # The stakes value for the 'month' in current year will be returned
            current_year = datetime.utcnow().strftime("%Y")
            part_key = f'{current_year}-{qp_month}'
        elif qp_month and qp_year:
            # The stakes value for the 'month' in particular 'year' will be returned
            part_key = f'{qp_year}-{qp_month}'
        else:
            # The stakes value for the current 'month' will be returned
            part_key = get_timestamp_id()

        item = get_db_item(table_name=table_values_name, part_key=part_key)
        # If item not exists return count and value = 0.
        response = {
            'timeframe': part_key,
            'stakes_count': item.get('stakes_count', 0),
            'stakes_value': item.get('stakes_value', 0)
        }
    else:
        # POST method
        # Get stake data from POST request
        stake_data = event['body']

        if sns_topic_arn:
            # Publish msg to SNS topic
            publish_to_sns(topic_arn=sns_topic_arn, stake=stake_data)

        # Put stake by transaction id (txid) into DynamoDB table
        # TODO: What with the stakes with the same txid? txid == epoch time of stake
        put_stake_txids_db(stake=stake_data, table_name=table_txid_name)

        # Put or update stakes value and stakes count for selected timestamp (time period):
        # - month row
        put_stake_values_db(table_name=table_values_name, stake=stake_data, timestamp=get_timestamp_id())
        # - year row
        put_stake_values_db(table_name=table_values_name, stake=stake_data, timestamp=get_timestamp_id(month=False))

        response = 'Tables updated and notification sent!'

    return {
        'statusCode': 200,
        'body': json.dumps(response)
    }
