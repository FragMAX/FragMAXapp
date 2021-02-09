from unittest import TestCase
from jobs.jobsd.jobids import JobIDs
from tests.utils import TempDirMixin


class TestJobIDs(TestCase, TempDirMixin):
    def setUp(self):
        self.setup_temp_dir()

    def tearDown(self):
        self.tear_down_temp_dir()

    def test_jobids(self):
        # check that creating JobIDs object without
        # persisted next ID works
        job_ids = JobIDs(self.temp_dir)
        self.assertEqual(job_ids.next(), "1")
        self.assertEqual(job_ids.next(), "2")

        # check that re-created JobIDs object loads
        # persisted next ID and continues IDs sequence
        job_ids = JobIDs(self.temp_dir)
        self.assertEqual(job_ids.next(), "3")
        self.assertEqual(job_ids.next(), "4")
