from pytest import fixture
from psutil import Popen, Process
import os

from check_new_stake import VerusProcess, VerusStakeChecker
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

