import psutil
import os

from check_new_stake import VerusProcess


def test_process_exist():
    # Run dummy process
    process_dummy = psutil.Popen(['sleep', '10'])
    process_dummy_name = psutil.Process(process_dummy.pid).name()
    process_to_test = VerusProcess(name=process_dummy_name)
    assert process_to_test.status is True
    assert process_to_test.directory == os.getcwd()
    # Terminate dummy process
    process_dummy.terminate()


def test_process_not_exist():
    # Dummy name
    process_dummy_name = 'test_process_qwerty123'
    process_to_test = VerusProcess(name=process_dummy_name)
    assert process_to_test.status is False
    assert process_to_test.directory == ''


