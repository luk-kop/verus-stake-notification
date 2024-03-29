import json
import boto3
import botocore.exceptions
import os
from datetime import datetime
from decimal import Decimal
from typing import Union


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


def lambda_handler_get(event, context) -> Union[dict, None]:
    """
    Main function.
    """
    # Load envs
    # Table that contains consolidated stake values for specific timestamp (time period).
    table_values_name = os.environ.get('DYNAMODB_VALUES_NAME')

    http_method = event.get('http_method')

    if http_method == 'GET':
        # Get and sanitize query params
        # Valid query params:
        # - year: '' or number in format '1234' (range 0001-9999)
        # - month" '' or number in format '02' (range 01-12)
        qp_year, qp_month = sanitize_query_params(year=event['year'], month=event['month'])

        # Define DynamoDB partition key value
        if qp_year and not qp_month:
            # The stakes amount for the whole 'year' will be returned
            part_key = f'{qp_year}'
        elif not qp_year and qp_month:
            # The stakes amount for the 'month' in current year will be returned
            current_year = datetime.utcnow().strftime("%Y")
            part_key = f'{current_year}-{qp_month}'
        elif qp_month and qp_year:
            # The stakes amount for the 'month' in particular 'year' will be returned
            part_key = f'{qp_year}-{qp_month}'
        else:
            # The stakes amount for the current 'month' will be returned
            part_key = get_timestamp_id()

        item = get_db_item(table_name=table_values_name, part_key=part_key)
        # If item not exists return count and amount = 0.
        response = {
            'timeframe': part_key,
            'stakes_count': item.get('stakes_count', 0),
            'stakes_amount': item.get('stakes_amount', 0)
        }

        return {
            'statusCode': 200,
            'body': json.dumps(response)
        }
