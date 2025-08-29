from pytest import fixture
from psutil import Popen, Process
import os
from typing import Dict, Tuple

import boto3
from moto import mock_aws

from new_stake_script.check_new_stake import (
    VerusProcess,
    VerusStakeChecker,
    StakeTransaction,
    StakeTransactions,
    ApiGatewayCognito,
)


def create_dummy_processes() -> Tuple:
    """
    Create dummy 'sleep' process and dummy 'VerusProcess'.
    """
    process_dummy = Popen(["sleep", "10"])
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
def nonexistent_process() -> VerusProcess:
    """
    Instantiate VerusProcess object with non-existed process.
    """
    process_dummy_name = "test_process_qwerty123"
    process_to_test = VerusProcess(name=process_dummy_name)
    return process_to_test


@fixture
def dummy_api_env_file_content() -> Dict:
    """
    Return dummy env_data for ApiGatewayCognito class.
    """
    dummy_env_data = {
        "COGNITO_TOKEN_URL": "https://test-token.url",
        "COGNITO_CLIENT_ID": "12345",
        "COGNITO_CLIENT_SECRET": "my-secret",
        "COGNITO_CUSTOM_SCOPES": "verus-api/api-test",
        "NOTIFICATION_API_URL": "https://test-notification.url",
    }
    return dummy_env_data


@fixture
def api_cognito(mocker, dummy_api_env_file_content):
    """
    Create ApiGatewayCognito object with mocked API env data.
    """
    # Mock _load_env_data() method
    mocker.patch.object(
        ApiGatewayCognito, "_load_env_data", return_value=dummy_api_env_file_content
    )
    api = ApiGatewayCognito()
    yield api


@fixture
def dummy_tx_hist_file_content() -> Dict:
    """
    Return initial tx file content.
    """
    content = {"txid_stake_previous": "", "txcount_previous": "0"}
    return content


@fixture
def verus_stake_checker(mocker, dummy_api_env_file_content, dummy_tx_hist_file_content):
    """
    Create VerusStakeChecker object with custom transactions (txs) history file.
    """
    file_tx_hist = "tx_history_test.json"
    file_api_env = ".api-env-test"
    # Mock API env file content
    mocker.patch.object(
        ApiGatewayCognito, "_get_env_data", return_value=dummy_api_env_file_content
    )
    # Mock tx history file creation
    mocker.patch.object(VerusStakeChecker, "_create_tx_hist_file")
    # Mock tx history file content
    mocker.patch.object(
        VerusStakeChecker, "_read_tx_hist_file", return_value=dummy_tx_hist_file_content
    )
    stake_checker = VerusStakeChecker(
        tx_hist_filename=file_tx_hist, env_api_filename=file_api_env
    )
    # Setup dummy processes
    process_dummy, process_to_test = create_dummy_processes()
    stake_checker.verus_process = process_to_test
    yield stake_checker
    process_dummy.terminate()


@fixture
def dummy_wallet_no_stake() -> Dict:
    """
    Return dummy Verus wallet info (no stake) with limited data.
    """
    wallet_info = {"immature_balance": 0.00000000, "txcount": 10}
    return wallet_info


@fixture
def dummy_wallet_new_stake() -> Dict:
    """
    Return dummy Verus wallet info (new stake) with limited data.
    """
    wallet_info = {"immature_balance": 12.00000000, "txcount": 11}
    return wallet_info


@fixture
def aws_credentials() -> None:
    """
    Mocked AWS Credentials for moto.
    """
    os.environ["AWS_ACCESS_KEY_ID"] = "testing"
    os.environ["AWS_SECRET_ACCESS_KEY"] = "testing"
    os.environ["AWS_SECURITY_TOKEN"] = "testing"
    os.environ["AWS_SESSION_TOKEN"] = "testing"


@fixture
# @mock_aws
def dynamodb(aws_credentials):
    """
    Create mocked DynamoDB service resource.
    """
    with mock_aws():
        yield boto3.resource("dynamodb")


@fixture
def aws_dummy_stake_txids_table(dynamodb):
    """
    Create a DynamoDB mocked verus_stakes_txids_table.
    """
    table_name = "verus_stakes_txids_table_test"
    table = dynamodb.create_table(
        TableName=table_name,
        AttributeDefinitions=[{"AttributeName": "tx_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "tx_id", "KeyType": "HASH"}],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    # Waits on the existence of the table before yielding
    table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
    yield table


@fixture
def aws_dummy_stake_values_table(dynamodb):
    """
    Create a DynamoDB mocked verus_stakes_values_table.
    """
    table_name = "verus_stakes_txids_table_test"
    table = dynamodb.create_table(
        TableName=table_name,
        AttributeDefinitions=[{"AttributeName": "ts_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "ts_id", "KeyType": "HASH"}],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    # Waits on the existence of the table before yield-ing
    table.meta.client.get_waiter("table_exists").wait(TableName=table_name)
    yield table


@fixture
def aws_dummy_dynamodb_both_tables(dynamodb):
    """
    Create a DynamoDB both mocked tables - for lambda_handler() func tests.
    """
    table_txids_name = "verus_stakes_txids_table_test"
    table_values_name = "verus_stakes_values_table_test"
    table_txids = dynamodb.create_table(
        TableName=table_txids_name,
        AttributeDefinitions=[{"AttributeName": "tx_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "tx_id", "KeyType": "HASH"}],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    table_values = dynamodb.create_table(
        TableName=table_values_name,
        AttributeDefinitions=[{"AttributeName": "ts_id", "AttributeType": "S"}],
        KeySchema=[{"AttributeName": "ts_id", "KeyType": "HASH"}],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 1, "WriteCapacityUnits": 1},
    )
    # Waits on the existence of the table before yielding
    table_txids.meta.client.get_waiter("table_exists").wait(TableName=table_txids_name)
    table_values.meta.client.get_waiter("table_exists").wait(
        TableName=table_values_name
    )
    # Assign the appropriate environment variables
    os.environ["DYNAMODB_VALUES_NAME"] = table_values.name
    os.environ["DYNAMODB_TXIDS_NAME"] = table_txids.name
    yield


@fixture
def dummy_stake_data() -> dict:
    """
    Return dummy Verus stake data.
    """
    stake_data = {"txid": "qwerty123456", "time": 1234567890, "amount": 123.123}
    return stake_data


@fixture
def dummy_lambda_event_get() -> dict:
    """
    Return dummy GET request data.
    """
    event_get = {"year": "2011", "month": "11", "http_method": "GET"}
    return event_get


@fixture
def dummy_lambda_event_post() -> dict:
    """
    Return dummy POST request data.
    """
    event_post = {
        "body": {"txid": "qwerty123456", "time": 1234567890, "amount": 123.123},
        "http_method": "POST",
    }
    return event_post


@fixture
def dummy_stake_txs() -> tuple:
    """
    Return a tuple of unordered and ordered dummy stake transactions (txs).
    """
    tx_01 = StakeTransaction(txid="tx01", time="100", amount=123, address="RXXX")
    tx_02 = StakeTransaction(txid="tx02", time="101", amount=12, address="RYYY")
    tx_03 = StakeTransaction(txid="tx03", time="102", amount=10, address="RYYY")
    tx_04 = StakeTransaction(txid="tx04", time="105", amount=1, address="RZZZ")
    return [tx_02, tx_04, tx_01, tx_03], [tx_01, tx_02, tx_03, tx_04]


@fixture
def dummy_stake_txs_collection(dummy_stake_txs) -> StakeTransactions:
    """
    Return a StakeTransactions object with collection of dummy stake txs.
    """
    stake_txs = StakeTransactions()
    dummy_stake_txs_unordered = dummy_stake_txs[0]
    for tx in dummy_stake_txs_unordered:
        stake_txs.add_stake_tx(tx)
    return stake_txs


@fixture
def dummy_list_txs() -> list:
    """
    Transactions returned by VerusStakeChecker's _process_call() method.
    """
    txs = [
        {
            "address": "RYYY",
            "category": "stake",
            "amount": 8000.00000000,
            "txid": "tx02",
            "time": 16327551319,
        },
        {
            "address": "RXXX",
            "category": "mint",
            "amount": 123.00000000,
            "txid": "tx01",
            "time": 1632750319,
        },
        {
            "address": "RXXX",
            "category": "mint",
            "amount": 10.00000000,
            "txid": "tx03",
            "time": 16327591319,
        },
    ]
    return txs
