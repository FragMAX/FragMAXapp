import unittest
import importlib
from unittest.mock import patch
from worker.ccp4 import _make_ccp4_maps

MTZ_DIR = "/mtz/dir"
MTZ_FILE = "some.mtz"
CCP4_FILE = "/mtz/dir/some_mFo-DFc.ccp4"


def _identity(func):
    return func


class TestMtzToMap(unittest.TestCase):
    @patch("redlock.RedLock")
    @patch("os.path.isfile")
    def test_task(self, isfile_mock, RedLockMock):
        # mock the case when ccp4 file(s) have been previously created
        isfile_mock.return_value = True
        with patch("worker.ccp4.celery.task", _identity):
            # reload ccp4 module, so that our mocked @celery.task decorator is applied
            import worker.ccp4
            importlib.reload(worker.ccp4)

            worker.ccp4.mtz_to_map(MTZ_DIR, MTZ_FILE)

            # check that correct lock was acquired and released
            RedLockMock.assert_called_once_with("mtz_to_map|/mtz/dir|some.mtz")
            lock = RedLockMock.return_value
            lock.acquire.assert_called_once_with()
            lock.release.assert_called_once_with()

            # check that path to ccp4 file was correct
            isfile_mock.assert_called_once_with(CCP4_FILE)


class TestMakeCCP4Maps(unittest.TestCase):
    """
    test _make_ccp4_maps() function
    """
    @patch("os.path.isfile")
    def test_cpp4_exists(self, isfile_mock):
        """
        the case when CCP4 file(s) already generated
        """
        isfile_mock.return_value = True
        _make_ccp4_maps(MTZ_DIR, MTZ_FILE)

        # check that path to ccp4 file was correct
        isfile_mock.assert_called_once_with(CCP4_FILE)

    @patch("os.path.isfile")
    @patch("subprocess.run")
    def test_cpp4_missing(self, run_mock, isfile_mock):
        """
        the case when CCP4 file(s) needs to be generated
        """

        isfile_mock.return_value = False
        _make_ccp4_maps(MTZ_DIR, MTZ_FILE)

        # check that path to ccp4 file was correct
        isfile_mock.assert_called_once_with(CCP4_FILE)

        # check that 'phenix' command was run with correct arguments
        run_mock.assert_called_once_with(["phenix.mtz2map", MTZ_FILE], cwd=MTZ_DIR)
