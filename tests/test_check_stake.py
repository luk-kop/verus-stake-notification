import os
from pathlib import Path


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


def test_txcount_history_file_created(verus_stake_checker):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess
    THEN txtcount history file has been created
    """
    filename = 'txcount_test.txt'
    assert os.path.exists(filename)


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


def test_wallet_info_txcount_last_on_start(verus_stake_checker):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess
    THEN last (historical) txtcount should be equal 0 on start
    """
    # Check txcount last value on start
    assert verus_stake_checker.txcount_last == '0'


def test_wallet_info_txcount_different(verus_stake_checker, dummy_wallet_no_stake):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data
    THEN different current and last (historical) txtcount values on VerusStakeChecker object creation (before run)
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    assert verus_stake_checker.txcount_last == '0'
    assert verus_stake_checker.txcount_current == '10'


def test_verus_state_checker_run_different_txcounts(verus_stake_checker, dummy_wallet_no_stake):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data
    THEN same current and last (historical) txtcount values after run VerusStakeChecker object
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    # Before run txcounts have different values
    assert verus_stake_checker.txcount_last != verus_stake_checker.txcount_current
    # After run txcounts should have the same values
    verus_stake_checker.run()
    assert verus_stake_checker.txcount_last == verus_stake_checker.txcount_current


def test_verus_state_checker_run_equal_txcounts(verus_stake_checker, dummy_wallet_no_stake):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data (no stake in wallet)
    THEN same txtcount values after run VerusStakeChecker object without new stake in wallet
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    # First run - after first run txcounts should have the same values
    verus_stake_checker.run()
    # Store txcounta after first run
    txcont_last_first_run = verus_stake_checker.txcount_last
    txcount_current_first_run = verus_stake_checker.txcount_current
    # Second run without new stake
    verus_stake_checker.run()
    # After the second run the txcounts should be equal to txcounts from first run
    assert verus_stake_checker.txcount_last == verus_stake_checker.txcount_current
    assert verus_stake_checker.txcount_last == txcont_last_first_run
    assert verus_stake_checker.txcount_current == txcount_current_first_run


def test_verus_state_checker_run_new_stake(verus_stake_checker, dummy_wallet_no_stake, dummy_wallet_new_stake):
    """
    GIVEN VerusStakeChecker object
    WHEN created VerusStakeChecker with dummy VerusProcess and dummy wallet info data (new stake in wallet)
    THEN different txtcount values after run VerusStakeChecker object with new stake in wallet
    """
    # Assign dummy wallet to wallet_info attribute
    verus_stake_checker.wallet_info = dummy_wallet_no_stake
    # First run - after first run txcounts should have the same values
    verus_stake_checker.run()
    txcont_last_first_run = verus_stake_checker.txcount_last
    txcount_current_first_run = verus_stake_checker.txcount_current
    # Second run with new stake
    verus_stake_checker.wallet_info = dummy_wallet_new_stake
    verus_stake_checker.run()
    # After the second run the txcounts should be different to txcounts from first run
    assert verus_stake_checker.txcount_last == verus_stake_checker.txcount_current
    assert verus_stake_checker.txcount_last != txcont_last_first_run
    assert verus_stake_checker.txcount_current != txcount_current_first_run





