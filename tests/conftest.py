from pytest import fixture
from psutil import Popen, Process

from check_new_stake import VerusProcess


@fixture
def dummy_process():
    """
    Run and terminate dummy process for tests.
    """
    # Setup dummy process
    process_dummy = Popen(['sleep', '10'])
    process_dummy_name = Process(process_dummy.pid).name()
    process_to_test = VerusProcess(name=process_dummy_name)
    yield process_to_test
    # Teardown dummy process
    process_dummy.terminate()


@fixture
def nonexistent_process():
    process_dummy_name = 'test_process_qwerty123'
    process_to_test = VerusProcess(name=process_dummy_name)
    return process_to_test
