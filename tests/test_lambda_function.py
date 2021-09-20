from datetime import date

from lambda_function import check_str_is_number, sanitize_query_params, get_timestamp_id, put_stake_txids_db


def test_item_not_exist_in_stake_txids_db(aws_dummy_stake_txids_table):
    """
    GIVEN Empty DynamoDB table.
    WHEN Get relevant item from DynamoDB table.
    THEN Item with specified 'tx_id' not exist.
    """
    response = aws_dummy_stake_txids_table.get_item(Key={'tx_id': 'qwerty123456'})
    item = response.get('Item', {})
    assert item == {}


def test_put_stake_txids_db_correct(aws_dummy_stake_txids_table,):
    """
    GIVEN Stake data from POST request.
    WHEN The stake data is put into a relevant DynamoDB table.
    THEN Item with desired 'tx_id' exist in relevant DynamoDB table and is correct.
    """
    table_name = aws_dummy_stake_txids_table.name
    stake = {
        'txid': 'qwerty123456',
        'time': 1234567890,
        'value': 123.123
    }
    put_stake_txids_db(stake=stake, table_name=table_name)
    response = aws_dummy_stake_txids_table.get_item(Key={'tx_id': 'qwerty123456'})
    item = response.get('Item', {})
    assert stake['time'] == item['stake_ts']
    assert stake['value'] == float(item['stake_value'])


def test_put_stake_txids_db_incorrect(aws_dummy_stake_txids_table):
    """
    GIVEN Stake data from POST request.
    WHEN The stake data is put into a relevant DynamoDB table.
    THEN Item with desired 'tx_id' exist in relevant DynamoDB table but is incorrect.
    """
    table_name = aws_dummy_stake_txids_table.name
    stake = {
        'txid': 'qwerty123456',
        'time': 1234567890,
        'value': 123.123
    }
    put_stake_txids_db(stake=stake, table_name=table_name)
    response = aws_dummy_stake_txids_table.get_item(Key={'tx_id': 'qwerty123456'})
    item = response.get('Item', {})
    assert 1234567891 != item['stake_ts']
    assert 123.321 != float(item['stake_value'])


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
    THEN Result is tuple with desired year and month values.
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
    THEN Result is tuple with empty string and month value.
    """
    result = sanitize_query_params(year='-123', month='01')
    assert result == ('', '01')


def test_sanitize_query_params_wrong_year_out_of_range_up():
    """
    GIVEN Out of range year and correct month params.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and month value.
    """
    result = sanitize_query_params(year='10000', month='01')
    assert result == ('', '01')


def test_sanitize_query_params_wrong_year_not_number():
    """
    GIVEN year param as a text and correct month param.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and month value.
    """
    result = sanitize_query_params(year='abc', month='01')
    assert result == ('', '01')


def test_sanitize_query_params_wrong_month_not_number():
    """
    GIVEN Correct year param and month param as a text.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and year value.
    """
    result = sanitize_query_params(year='2021', month='aws')
    assert result == ('2021', '')


def test_sanitize_query_params_wrong_month_out_of_range_up():
    """
    GIVEN Correct year param and month value out of range.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and year value.
    """
    result = sanitize_query_params(year='2021', month='13')
    assert result == ('2021', '')


def test_sanitize_query_params_wrong_month_out_of_range_down():
    """
    GIVEN Correct year param and month value out of range.
    WHEN sanitize_query_params() fun is invoked.
    THEN Result is tuple with empty string and year value.
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