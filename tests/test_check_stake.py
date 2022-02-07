import os
from pathlib import Path
from unittest import mock

from new_stake_script.check_new_stake import StakeTransaction, StakeTransactions, VerusStakeChecker


def test_process_exist(dummy_process):
    """
    GIVEN VerusProcess object
    WHEN created VerusProcess object with 'name' attribute that represent existed process
    THEN declared process exist
    """
    assert dummy_process.status is True


def test_process_exist_directory(dummy_process):
    """
    GIVEN VerusProcess object
    WHEN created VerusProcess object with 'name' attribute that represent existed process
    THEN declared process's base directory is cwd
    """
    assert dummy_process.directory == os.getcwd()


def test_process_not_exist(nonexistent_process):
    """
    GIVEN VerusProcess object
    WHEN created VerusProcess object with 'name' attribute that represent non-existed process
    THEN declared process not exist
    """
    assert nonexistent_process.status is False


def test_process_not_exist_directory(nonexistent_process):
    """
    GIVEN VerusProcess object
    WHEN created VerusProcess object with 'name' attribute that represent non-existed process
    THEN declared process's base directory is ''
    """
    assert nonexistent_process.directory == ''


def test_verus_script_path(verus_stake_checker):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess
    THEN script's base directory is cwd + script name
    """
    script_path = verus_stake_checker.verus_script_path
    assert script_path == Path(os.getcwd()).joinpath('verus')


def test_wallet_info_txcount_current(verus_stake_checker, dummy_wallet_no_stake):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data
    THEN current txtcount changed to value from dummy wallet info
    """
    # Check txcount value without wallet_info data
    assert verus_stake_checker.txcount_current == '0'
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    assert verus_stake_checker.txcount_current == '10'


def test_wallet_info_txcount_hist_on_start(verus_stake_checker):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess
    THEN last (historical) txtcount should be equal 0 on start
    """
    # Check txcount last value on start
    assert verus_stake_checker.txcount_hist == '0'


def test_wallet_info_txcount_different(verus_stake_checker, dummy_wallet_no_stake):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data
    THEN different current and last (historical) txtcount values on VerusStakeChecker object creation (before run)
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    assert verus_stake_checker.txcount_hist == '0'
    assert verus_stake_checker.txcount_current == '10'


def test_verus_state_checker_run_different_txcounts(mocker, verus_stake_checker, dummy_wallet_no_stake, dummy_list_txs):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data
    THEN same current and last (historical) txtcount values after run VerusStakeChecker object
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    # Before run txcounts have different values
    assert verus_stake_checker.txcount_hist != verus_stake_checker.txcount_current
    # Mock _process_call() method
    mocker.patch.object(VerusStakeChecker, '_process_call', return_value=dummy_list_txs)
    # After run txcounts should have the same values
    verus_stake_checker.run()
    assert verus_stake_checker.txcount_hist == verus_stake_checker.txcount_current


def test_verus_state_checker_run_equal_txcounts(mocker, verus_stake_checker, dummy_wallet_no_stake, dummy_list_txs):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data (no stake in wallet)
    THEN same txtcount values after run VerusStakeChecker object without new stake in wallet
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    # Mock _process_call() method
    mocker.patch.object(VerusStakeChecker, '_process_call', return_value=dummy_list_txs)
    # First run - after first run txcounts should have the same values
    verus_stake_checker.run()
    # Store txcounta after first run
    txcont_last_first_run = verus_stake_checker.txcount_hist
    txcount_current_first_run = verus_stake_checker.txcount_current
    # Second run without new stake
    verus_stake_checker.run()
    # After the second run the txcounts should be equal to txcounts from first run
    assert verus_stake_checker.txcount_hist == verus_stake_checker.txcount_current
    assert verus_stake_checker.txcount_hist == txcont_last_first_run
    assert verus_stake_checker.txcount_current == txcount_current_first_run


def test_verus_state_checker_run_new_stake(mocker, verus_stake_checker, dummy_wallet_no_stake,
                                           dummy_wallet_new_stake, dummy_list_txs):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data (new stake in wallet)
    THEN different txtcount values after run VerusStakeChecker object with new stake in wallet
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    # Mock _process_call() method
    mocker.patch.object(VerusStakeChecker, '_process_call', return_value=dummy_list_txs)
    # First run - after first run txcounts should have the same values
    verus_stake_checker.run()
    txcont_last_first_run = verus_stake_checker.txcount_hist
    txcount_current_first_run = verus_stake_checker.txcount_current
    # Second run with new stake
    verus_stake_checker.wallet_info = dummy_wallet_new_stake
    verus_stake_checker.run()
    # After the second run the txcounts should be different to txcounts from first run
    assert verus_stake_checker.txcount_hist == verus_stake_checker.txcount_current
    assert verus_stake_checker.txcount_hist != txcont_last_first_run
    assert verus_stake_checker.txcount_current != txcount_current_first_run


def test_stake_transaction_correct():
    """
    GIVEN dummy stake tx
    WHEN StakeTransaction object is created
    THEN StakeTransaction object's attributes are correct
    """
    dummy_tx = {
        'address': 'RXXX',
        'category': 'mint',
        'amount': 12.00000000,
        'txid': 'tx01',
        'time': 1632511111
    }
    tx = StakeTransaction(
        txid=dummy_tx['txid'],
        time=dummy_tx['time'],
        amount=dummy_tx['amount'],
        address=dummy_tx['address']
    )
    assert tx.txid == 'tx01'
    assert tx.time == 1632511111
    assert tx.amount == 12.00000000
    assert tx.address == 'RXXX'


def test_stake_transactions_correct_order(dummy_stake_txs):
    """
    GIVEN several dummy stake txs
    WHEN StakeTransactions object is created and dummy txs are added to StakeTransactions collection
    THEN Stake txs are returned in desired order
    """
    stake_txs = StakeTransactions()
    dummy_stake_txs_unordered, dummy_stake_txs_ordered = dummy_stake_txs
    for tx in dummy_stake_txs_unordered:
        stake_txs.add_stake_tx(tx)
    # Not sorted txs
    assert stake_txs.txs == dummy_stake_txs_unordered
    # Sorted txs
    assert stake_txs.txs_sorted == dummy_stake_txs_ordered


def test_stake_transactions_stakes_txids(dummy_stake_txs_collection):
    """
    GIVEN StakeTransactions object with collection of several dummy stake txs
    WHEN StakeTransactions stakes_txids attribute is called
    THEN wallet's stake txids are returned in desired order
    """
    stake_txs = dummy_stake_txs_collection
    most_recent_stake_txid = stake_txs.stakes_txids
    assert most_recent_stake_txid == ['tx01', 'tx02', 'tx03', 'tx04']


def test_stake_transactions_get_last_stake_txid(dummy_stake_txs_collection):
    """
    GIVEN StakeTransactions object with collection of several dummy stake txs
    WHEN method get_last_stake_txid() on StakeTransactions object is called
    THEN most recent (last) txid in wallet is returned
    """
    stake_txs = dummy_stake_txs_collection
    most_recent_stake_txid = stake_txs.get_last_stake_txid()
    assert most_recent_stake_txid == 'tx04'


def test_stake_transactions_get_tx_exist(dummy_stake_txs_collection):
    """
    GIVEN StakeTransactions object with collection of several dummy stake txs
    WHEN method get_stake_tx() with an existing stake tx is called
    THEN the appropriate stake tx is returned
    """
    stake_txs = dummy_stake_txs_collection
    tx_01 = stake_txs.get_stake_tx(txid='tx01')
    tx_04 = stake_txs.get_stake_tx(txid='tx04')
    assert tx_01.txid == 'tx01'
    assert tx_04.txid == 'tx04'


def test_stake_transactions_get_tx_not_exist(dummy_stake_txs_collection):
    """
    GIVEN StakeTransactions object with collection of several dummy stake txs
    WHEN method get_stake_tx() with not existing stake tx is called
    THEN the appropriate stake tx is returned
    """
    stake_txs = dummy_stake_txs_collection
    tx_01 = stake_txs.get_stake_tx(txid='1111')
    tx_04 = stake_txs.get_stake_tx(txid='2222')
    assert tx_01 is None
    assert tx_04 is None


def test_stake_transactions_get_new_stakes(dummy_stake_txs_collection):
    """
    GIVEN StakeTransactions object with collection of several dummy stake txs
    WHEN method get_new_stakes_txs() with specified stake txid is called
    THEN the list of newer txs than the specified txid is returned
    """
    stake_txs = dummy_stake_txs_collection
    new_stake_txs = stake_txs.get_new_stakes_txs(txid_last='tx02')
    new_stake_txids = [tx.txid for tx in new_stake_txs]
    assert new_stake_txids == ['tx03', 'tx04']


def test_stake_transactions_get_new_stakes_txid_recent(dummy_stake_txs_collection):
    """
    GIVEN StakeTransactions object with collection of several dummy stake txs
    WHEN method get_new_stakes_txs() with last (most recent) stake txid is called
    THEN the empty list is returned
    """
    stake_txs = dummy_stake_txs_collection
    new_stake_txs = stake_txs.get_new_stakes_txs(txid_last='tx04')
    new_stake_txids = [tx.txid for tx in new_stake_txs]
    assert new_stake_txids == []


def test_stake_transactions_get_new_stakes_txid_not_exist(dummy_stake_txs_collection):
    """
    GIVEN StakeTransactions object with collection of several dummy stake txs
    WHEN method get_new_stakes_txs() with non-existent stake txid is called
    THEN the empty list is returned
    """
    stake_txs = dummy_stake_txs_collection
    new_stake_txs = stake_txs.get_new_stakes_txs(txid_last='xxx')
    new_stake_txids = [tx.txid for tx in new_stake_txs]
    assert new_stake_txids == []


def test_api_gateway_cognito(dummy_api_env_file_content, api_cognito):
    """
    GIVEN dummy env_data
    WHEN created ApiGatewayCognito object with specified env_data
    THEN object's attributes data is equal to specified in env_data
    """
    assert api_cognito.cognito_token_url == dummy_api_env_file_content['COGNITO_TOKEN_URL']
    assert api_cognito.cognito_client_id == dummy_api_env_file_content['COGNITO_CLIENT_ID']
    assert api_cognito.cognito_client_secret == dummy_api_env_file_content['COGNITO_CLIENT_SECRET']
    assert api_cognito.scopes == dummy_api_env_file_content['COGNITO_CUSTOM_SCOPES']
    assert api_cognito.api_gateway_url == dummy_api_env_file_content['NOTIFICATION_API_URL']


def test_api_gateway_cognito_check_response_status_200(api_cognito):
    """
    GIVEN ApiGatewayCognito object with dummy env_data
    WHEN invoked _check_response_status() method with response status_code = 200
    THEN None is returned
    """
    mocked_response_obj = mock.Mock()
    mocked_response_obj.status_code = 200
    assert api_cognito._check_response_status(mocked_response_obj) is None


def test_api_gateway_cognito_check_response_status_not_200(mocker, api_cognito):
    """
    GIVEN ApiGatewayCognito object with dummy env_data
    WHEN invoked _check_response_status() method with response status_code != 200
    THEN sys.exit is called
    """
    # Mock logger attr
    mocker.patch.object(api_cognito, 'logger')
    # Mock HTTP response
    mocked_response_obj = mock.Mock()
    mocked_response_obj.status_code = 404
    mocked_response_obj.text = 'Sth is wrong'
    mocked_exit = mocker.patch('sys.exit')
    api_cognito._check_response_status(response=mocked_response_obj)
    # Assertions
    mocked_exit.assert_called_once()
    mocked_exit.assert_called()


def test_api_gateway_cognito_check_response_status_not_200_logger(mocker, api_cognito):
    """
    GIVEN ApiGatewayCognito object with dummy env_data
    WHEN invoked _check_response_status() method with response status_code != 200
    THEN desired log entry is created
    """
    mocked_response_obj = mock.Mock()
    mocked_response_obj.status_code = 404
    mocked_response_obj.text = 'Sth is wrong'
    mocker.patch('sys.exit')
    # mocked_logger = mocker.patch('new_stake_script.check_new_stake.logger')
    mocked_logger = mocker.patch.object(api_cognito, 'logger')
    desired_log_entry = f'API response: {mocked_response_obj.status_code} {mocked_response_obj.text}'
    api_cognito._check_response_status(response=mocked_response_obj)
    # Assertions
    mocked_logger.error.assert_called_with(desired_log_entry)


def test_api_gateway_cognito_get_access_token(mocker, api_cognito):
    """
    GIVEN ApiGatewayCognito object with dummy env_data
    WHEN invoked _get_access_token() method
    THEN valid access_token is returned
    """
    # Mock requests.post method
    mocked_post = mocker.patch('requests.post', autospec=True)
    mocked_response_obj = mock.Mock()
    mocked_response_obj.status_code = 200
    mocked_response_obj.json = lambda: {'access_token': 'valid-token'}
    mocked_post.return_value = mocked_response_obj
    # Mock requests.post
    assert api_cognito._get_access_token() == 'valid-token'


def test_api_gateway_cognito_check_http_method_not_allowed(mocker, api_cognito):
    """
    GIVEN ApiGatewayCognito object with dummy env_data
    WHEN invoked _check_method_is_allowed() method with not-allowed HTTP method
    THEN sys.exit is called
    """
    # Mock logger attr
    mocker.patch.object(api_cognito, 'logger')
    # Mock sys.exit method
    mocked_exit = mocker.patch('sys.exit')
    api_cognito.check_http_method(method='PUT')
    # Assertions
    mocked_exit.assert_called_once()
    mocked_exit.assert_called()


def test_api_gateway_cognito_check_http_method_allowed(mocker, api_cognito):
    """
    GIVEN ApiGatewayCognito object with dummy env_data
    WHEN invoked _check_method_is_allowed() method with allowed HTTP methods
    THEN None is returned
    """
    for method in ['POST', 'GET', 'get', 'post']:
        assert api_cognito.check_http_method(method=method) is None
