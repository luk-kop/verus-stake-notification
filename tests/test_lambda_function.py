from datetime import date
import json

from lambda_functions.lambda_function_post import get_timestamp_id, put_stake_txids_db, put_stake_values_db, get_db_item, \
    update_db_item, lambda_handler_post
from lambda_functions.lambda_function_get import check_str_is_number, sanitize_query_params, lambda_handler_get


def test_item_not_exist_in_stake_txids_db(aws_dummy_stake_txids_table):
    """
    GIVEN Empty DynamoDB table.
    WHEN Get relevant item from DynamoDB table.
    THEN Item with specified 'tx_id' not exist.
    """
    response = aws_dummy_stake_txids_table.get_item(Key={'tx_id': 'qwerty123456'})
    item = response.get('Item', {})
    assert item == {}


def test_item_not_exist_in_stake_values_db(aws_dummy_stake_values_table):
    """
    GIVEN Empty DynamoDB table.
    WHEN Get relevant item from DynamoDB table.
    THEN Item with specified 'ts_id' not exist.
    """
    response = aws_dummy_stake_values_table.get_item(Key={'ts_id': '2021-08'})
    item = response.get('Item', {})
    assert item == {}


def test_put_stake_txids_db_correct(aws_dummy_stake_txids_table, dummy_stake_data):
    """
    GIVEN Stake data from POST request.
    WHEN The stake data is put into a relevant DynamoDB table.
    THEN Item with desired 'tx_id' exist in relevant DynamoDB table and is correct.
    """
    table_name = aws_dummy_stake_txids_table.name
    put_stake_txids_db(stake=dummy_stake_data, table_name=table_name)
    response = aws_dummy_stake_txids_table.get_item(Key={'tx_id': 'qwerty123456'})
    item = response.get('Item', {})
    assert dummy_stake_data['time'] == item['stake_ts']
    assert dummy_stake_data['amount'] == float(item['stake_amount'])


def test_put_stake_txids_db_incorrect(aws_dummy_stake_txids_table, dummy_stake_data):
    """
    GIVEN Stake data from POST request.
    WHEN The stake data is put into a relevant DynamoDB table.
    THEN Item with desired 'tx_id' exist in relevant DynamoDB table but is incorrect.
    """
    table_name = aws_dummy_stake_txids_table.name
    put_stake_txids_db(stake=dummy_stake_data, table_name=table_name)
    response = aws_dummy_stake_txids_table.get_item(Key={'tx_id': 'qwerty123456'})
    item = response.get('Item', {})
    assert 1234567891 != item['stake_ts']
    assert 123.321 != float(item['stake_amount'])


def test_put_stake_values_db_correct_year_month(aws_dummy_stake_values_table, dummy_stake_data):
    """
    GIVEN Stake data from POST request.
    WHEN The stake data is put into a relevant DynamoDB table.
    THEN Item with desired 'ts_id' exist in relevant DynamoDB table and is correct.
    """
    table_name = aws_dummy_stake_values_table.name
    put_stake_values_db(table_name=table_name, stake=dummy_stake_data, timestamp='2021-01')
    response = aws_dummy_stake_values_table.get_item(Key={'ts_id': '2021-01'})
    item = response.get('Item', {})
    assert int(item['stakes_count']) == 1
    assert float(item['stakes_amount']) == 123.123


def test_put_stake_values_db_correct_year(aws_dummy_stake_values_table, dummy_stake_data):
    """
    GIVEN Stake data from POST request.
    WHEN The stake data is put into a relevant DynamoDB table.
    THEN Item with desired 'ts_id' exist in relevant DynamoDB table and is correct.
    """
    table_name = aws_dummy_stake_values_table.name
    put_stake_values_db(table_name=table_name, stake=dummy_stake_data, timestamp='2021')
    response = aws_dummy_stake_values_table.get_item(Key={'ts_id': '2021'})
    item = response.get('Item', {})
    assert int(item['stakes_count']) == 1
    assert float(item['stakes_amount']) == 123.123


def test_get_db_item_not_exist(aws_dummy_stake_values_table):
    """
    GIVEN Stake data from POST request.
    WHEN The request for the corresponding item is made to the DynamoDB table.
    THEN Item with desired 'ts_id' not exist in relevant DynamoDB table.
    """
    table_name = aws_dummy_stake_values_table.name
    response = get_db_item(table_name=table_name, part_key='2020')
    item = response.get('Item', {})
    assert item == {}


def test_get_db_item_exist_year_month(aws_dummy_stake_values_table, dummy_stake_data):
    """
    GIVEN Stake data from POST request.
    WHEN The request for the corresponding item is made to the DynamoDB table.
    THEN Item with desired 'ts_id' exist in relevant DynamoDB table.
    """
    table_name = aws_dummy_stake_values_table.name
    # Put dummy data into table
    put_stake_values_db(table_name=table_name, stake=dummy_stake_data, timestamp='2019-01')
    item = get_db_item(table_name=table_name, part_key='2019-01')
    assert item


def test_get_db_item_exist_year(aws_dummy_stake_values_table, dummy_stake_data):
    """
    GIVEN Stake data from POST request.
    WHEN The request for the corresponding item is made to the DynamoDB table.
    THEN Item with desired 'ts_id' exist in relevant DynamoDB table.
    """
    table_name = aws_dummy_stake_values_table.name
    # Put dummy data into table
    put_stake_values_db(table_name=table_name, stake=dummy_stake_data, timestamp='2019')
    item = get_db_item(table_name=table_name, part_key='2019')
    assert item


def test_get_db_item_year_and_year_month(aws_dummy_stake_values_table, dummy_stake_data):
    """
    GIVEN Stake data from POST request.
    WHEN The request for the corresponding items is made to the DynamoDB table.
    THEN Items with desired 'ts_id' exist in relevant DynamoDB table.
    """
    table_name = aws_dummy_stake_values_table.name
    # Put dummy data into table
    put_stake_values_db(table_name=table_name, stake=dummy_stake_data, timestamp='2021-03')
    put_stake_values_db(table_name=table_name, stake=dummy_stake_data, timestamp='2021')
    item_year = get_db_item(table_name=table_name, part_key='2021')
    item_year_month = get_db_item(table_name=table_name, part_key='2021-03')
    assert item_year
    assert item_year_month


def test_update_db_item(aws_dummy_stake_values_table, dummy_stake_data):
    """
    GIVEN Stake data to update with relevant timestamp.
    WHEN Executing the update of an item in the DynamoDB table.
    THEN Items with desired 'ts_id' is updated.
    """
    table_name = aws_dummy_stake_values_table.name
    timestamp = '2021-03'
    updated_stake_data = {
        'stakes_amount': 150.1,
        'stakes_count': 2
    }
    # Put dummy data into table
    put_stake_values_db(table_name=table_name, stake=dummy_stake_data, timestamp=timestamp)
    update_db_item(table_name=table_name, part_key=timestamp, updated_data=updated_stake_data)
    item = get_db_item(table_name=table_name, part_key=timestamp)
    assert int(item['stakes_count']) == 2
    assert float(item['stakes_amount']) == 150.1


def test_lambda_handler_get_request(aws_dummy_dynamodb_both_tables, dummy_lambda_event_get):
    """
    GIVEN Lambda event for GET request.
    WHEN Executing the lambda_handler() func.
    THEN Desired func return.
    """
    response_test = lambda_handler_get(event=dummy_lambda_event_get, context={})
    response_desired = {
        'timeframe': '2011-11',
        'stakes_count': 0,
        'stakes_amount': 0
    }
    body = {
        'statusCode': 200,
        'body': json.dumps(response_desired)
    }
    assert response_test == body


def test_lambda_handler_post_request(aws_dummy_dynamodb_both_tables, dummy_lambda_event_post):
    """
    GIVEN Lambda event for POST request.
    WHEN Executing the lambda_handler() func.
    THEN Desired func return.
    """
    response_test = lambda_handler_post(event=dummy_lambda_event_post, context={})
    response_desired = {
        'statusCode': 200,
        'body': json.dumps('Tables updated and notification sent!')
    }
    assert response_test == response_desired


def test_check_str_is_number_pos_int():
    """
    GIVEN String value - positive integer.
    WHEN check_str_is_number() fun is invoked.
    THEN String is a number.
    """
    value = '123'
    assert check_str_is_number(value=value)


def test_check_str_is_number_neg_int():
    """
    GIVEN String value - negative integer.
    WHEN check_str_is_number() fun is invoked
    THEN String is a number.
    """
    value = '-123'
    assert check_str_is_number(value=value)


def test_check_str_is_number_pos_float():
    """
    GIVEN String value - positive float.
    WHEN check_str_is_number() fun is invoked
    THEN String is a number.
    """
    value = '123.123'
    assert check_str_is_number(value=value)


def test_check_str_is_number_neg_float():
    """
    GIVEN String value - negative float.
    WHEN check_str_is_number() fun is invoked
    THEN String is a number.
    """
    value = '-123.123'
    assert check_str_is_number(value=value)


def test_check_str_is_number_not_number():
    """
    GIVEN String value - text.
    WHEN check_str_is_number() fun is invoked
    THEN String is not a number.
    """
    value = 'aws'
    assert not check_str_is_number(value=value)


def test_sanitize_query_params_correct_values():
    """
    GIVEN Correct year and month params.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with desired year and month amount.
    """
    result = sanitize_query_params(year='2021', month='01')
    assert result == ('2021', '01')


def test_sanitize_query_params_no_values():
    """
    GIVEN Correct year and month params - empty strings.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty strings.
    """
    result = sanitize_query_params(year='', month='')
    assert result == ('', '')


def test_sanitize_query_params_only_year():
    """
    GIVEN Correct year and empty month params.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with correct year and empty month.
    """
    result = sanitize_query_params(year='2021', month='')
    assert result == ('2021', '')


def test_sanitize_query_params_only_month():
    """
    GIVEN Empty year and correct month params.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty year and correct month.
    """
    result = sanitize_query_params(year='', month='1')
    assert result == ('', '01')


def test_sanitize_query_params_wrong_year_out_of_range_down():
    """
    GIVEN Out of range year and correct month params.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and month amount.
    """
    result = sanitize_query_params(year='-123', month='01')
    assert result == ('', '01')


def test_sanitize_query_params_wrong_year_out_of_range_up():
    """
    GIVEN Out of range year and correct month params.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and month amount.
    """
    result = sanitize_query_params(year='10000', month='01')
    assert result == ('', '01')


def test_sanitize_query_params_wrong_year_not_number():
    """
    GIVEN year param as a text and correct month param.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and month amount.
    """
    result = sanitize_query_params(year='abc', month='01')
    assert result == ('', '01')


def test_sanitize_query_params_wrong_month_not_number():
    """
    GIVEN Correct year param and month param as a text.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and year amount.
    """
    result = sanitize_query_params(year='2021', month='aws')
    assert result == ('2021', '')


def test_sanitize_query_params_wrong_month_out_of_range_up():
    """
    GIVEN Correct year param and month amount out of range.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and year amount.
    """
    result = sanitize_query_params(year='2021', month='13')
    assert result == ('2021', '')


def test_sanitize_query_params_wrong_month_out_of_range_down():
    """
    GIVEN Correct year param and month amount out of range.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and year amount.
    """
    result = sanitize_query_params(year='2021', month='0')
    assert result == ('2021', '')


def test_get_timestamp_id_year_month():
    """
    GIVEN Sample date object.
    WHEN get_timestamp_id() fun is invoked with default year & month params.
    THEN Result is string in desired format - 'YYYY-MM'.
    """
    test_date = date(2021, 1, 12)
    result = get_timestamp_id(date=test_date)
    assert result == '2021-01'


def test_get_timestamp_id_only_year():
    """
    GIVEN Sample date object.
    WHEN get_timestamp_id() fun is invoked with month = False and year default params.
    THEN Result is string in desired format - 'YYYY'.
    """
    test_date = date(2021, 1, 12)
    result = get_timestamp_id(month=False, date=test_date)
    assert result == '2021'


def test_get_timestamp_id_only_month():
    """
    GIVEN Sample date object.
    WHEN get_timestamp_id() fun is invoked with year = False and month default params.
    THEN Result is string in desired format -' MM'.
    """
    test_date = date(2021, 1, 12)
    result = get_timestamp_id(year=False, date=test_date)
    assert result == '01'