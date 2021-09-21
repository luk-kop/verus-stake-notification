from pytest import fixture
from psutil import Popen, Process
import os

import boto3
from moto import mock_dynamodb2

from new_stake_script.check_new_stake import VerusProcess, VerusStakeChecker
from resources.aws_policy_document import PolicyStatement


def create_dummy_processes():
    """
    Create dummy 'sleep' process and dummy 'VerusProcess'.
    """
    process_dummy = Popen(['sleep', '10'])
    process_dummy_name = Process(process_dummy.pid).name()
    return process_dummy, VerusProcess(name=process_dummy_name)


@fixture
def dummy_process():
    """
    Run and terminate dummy process for tests.
    """
    # Setup dummy processes
    process_dummy, process_to_test = create_dummy_processes()
    yield process_to_test
    # Teardown dummy process
    process_dummy.terminate()


@fixture
def nonexistent_process():
    """
    Instantiate VerusProcess object with non-existed process.
    """
    process_dummy_name = 'test_process_qwerty123'
    process_to_test = VerusProcess(name=process_dummy_name)
    return process_to_test


@fixture
def verus_stake_checker():
    """
    Create VerusStakeChecker() object with custom txcount history file.
    """
    filename = 'txcount_test.txt'
    stake_checker = VerusStakeChecker(txcount_history_file_name=filename)
    # Setup dummy processes
    process_dummy, process_to_test = create_dummy_processes()
    stake_checker.verus_process = process_to_test
    yield stake_checker
    # Remove filename after test completion
    os.remove(filename)
    # Teardown dummy process
    process_dummy.terminate()


@fixture
def dummy_wallet_no_stake():
    """
    Return dummy Verus wallet info (no stake) with limited data.
    """
    wallet_info = {
        'immature_balance': 0.00000000,
        'txcount': 10
    }
    return wallet_info


@fixture
def dummy_wallet_new_stake():
    """
    Return dummy Verus wallet info (new stake) with limited data.
    """
    wallet_info = {
        'immature_balance': 12.00000000,
        'txcount': 11
    }
    return wallet_info


@fixture
def dummy_policy_statement():
    """
    Return dummy policy statement.
    """
    policy_statement = PolicyStatement(effect='Allow',
                                       actions=['execute-api:Invoke'],
                                       resources=['execute-api:/*'])
    return policy_statement


@fixture
def dynamodb():
    """
    Create mocked DynamoDB service resource.
    """
    with mock_dynamodb2():
        yield boto3.resource('dynamodb')


@fixture
def aws_dummy_stake_txids_table(dynamodb):
    """
    Create a DynamoDB mocked verus_stakes_txids_table.
    """
    table_name = 'verus_stakes_txids_table_test'
    table = dynamodb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {
                'AttributeName': 'tx_id',
                'AttributeType': 'S'
            }
        ],
        KeySchema=[
            {
                'AttributeName': 'tx_id',
                'KeyType': 'HASH'
            }
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        },
    )
    # Waits on the existence of the table before yielding
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    yield table


@fixture
def aws_dummy_stake_values_table(dynamodb):
    """
    Create a DynamoDB mocked verus_stakes_values_table.
    """
    table_name = 'verus_stakes_txids_table_test'
    table = dynamodb.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {
                'AttributeName': 'ts_id',
                'AttributeType': 'S'
            }
        ],
        KeySchema=[
            {
                'AttributeName': 'ts_id',
                'KeyType': 'HASH'
            }
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        },
    )
    # Waits on the existence of the table before yield-ing
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    yield table


@fixture
def aws_dummy_dynamodb_both_tables(dynamodb):
    """
    Create a DynamoDB both mocked tables - for lambda_handler() func tests.
    """
    table_txids_name = 'verus_stakes_txids_table_test'
    table_values_name = 'verus_stakes_values_table_test'
    table_txids = dynamodb.create_table(
        TableName=table_txids_name,
        AttributeDefinitions=[
            {
                'AttributeName': 'tx_id',
                'AttributeType': 'S'
            }
        ],
        KeySchema=[
            {
                'AttributeName': 'tx_id',
                'KeyType': 'HASH'
            }
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        },
    )
    table_values = dynamodb.create_table(
        TableName=table_values_name,
        AttributeDefinitions=[
            {
                'AttributeName': 'ts_id',
                'AttributeType': 'S'
            }
        ],
        KeySchema=[
            {
                'AttributeName': 'ts_id',
                'KeyType': 'HASH'
            }
        ],
        BillingMode='PROVISIONED',
        ProvisionedThroughput={
            'ReadCapacityUnits': 1,
            'WriteCapacityUnits': 1
        },
    )
    # Waits on the existence of the table before yielding
    table_txids.meta.client.get_waiter('table_exists').wait(TableName=table_txids_name)
    table_values.meta.client.get_waiter('table_exists').wait(TableName=table_values_name)
    # Assign the appropriate environment variables
    os.environ['DYNAMODB_VALUES_NAME'] = table_values.name
    os.environ['DYNAMODB_TXIDS_NAME'] = table_txids.name
    yield


@fixture
def dummy_stake_data():
    """
    Return dummy Verus stake data.
    """
    stake_data = {
        'txid': 'qwerty123456',
        'time': 1234567890,
        'value': 123.123
    }
    return stake_data


@fixture
def dummy_lambda_event_get():
    """
    Return dummy GET request data.
    """
    event_get = {
        'year': '2011',
        'month': '11',
        'http_method': 'GET'
    }
    return event_get


@fixture
def dummy_lambda_event_post():
    """
    Return dummy POST request data.
    """
    event_post = {
        'body': {
            'txid': 'qwerty123456',
            'time': 1234567890,
            'value': 123.123
        },
        'http_method': 'POST'}
    return event_post


