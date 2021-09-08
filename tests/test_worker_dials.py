import unittest
import importlib
from unittest.mock import patch
from tests.utils import identity, WorkerTaskTester
from worker.dials import _make_rlp_json


DIALS_DIR = "/dials/dir"
RLP_FILE = "/dials/dir/rlp.json"


class TestGetRlp(WorkerTaskTester):
    @patch("redlock.RedLock")
    @patch("os.path.isfile")
    def test_task(self, isfile_mock, red_lock_mock):
        # mock the case when ccp4 file(s) have been previously created
        isfile_mock.return_value = True
        with patch("worker.dials.celery.task", identity):
            # reload ccp4 module, so that our mocked @celery.task decorator is applied
            import worker.dials
            importlib.reload(worker.dials)

            worker.dials.get_rlp(DIALS_DIR)

            # check that correct lock was acquired and released
            self.assert_locking(red_lock_mock, "get_rlp|/dials/dir")

            # check that path to RLP file was correct
            isfile_mock.assert_called_once_with(RLP_FILE)


@patch("os.path.isfile")
class TestMakeRlpJson(unittest.TestCase):
    """
    test _make_rlp_json function
    """
    def test_rlp_exists(self, isfile_mock):
        isfile_mock.return_value = True
        _make_rlp_json(DIALS_DIR)

        # check that path to ccp4 file was correct
        isfile_mock.assert_called_once_with(RLP_FILE)

    @patch("fragview.hpc.frontend_run")
    def test_rlp_missing(self, hpc_run_mock, isfile_mock):
        isfile_mock.return_value = False
        _make_rlp_json(DIALS_DIR)

        call_arg = hpc_run_mock.call_args[0][0]
        self.assertRegex(call_arg, f"^cd {DIALS_DIR}.*dials.export")
