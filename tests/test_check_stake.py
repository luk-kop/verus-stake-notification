import os


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


