import socket
from pathlib import Path
from threading import Thread
from unittest.mock import patch
from projects.database import db_session
from fragview.sites.current import get_hpc_runner
from jobs.client import JobsSet, cancel_jobs
from tests.utils import ProjectTestCase


class SockServer:
    READ_CHUNK_SIZE = 1024

    def __init__(self, socket_path: str):
        self.received = ""

        server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        server.bind(str(socket_path))
        server.listen(1)

        self.thread = Thread(target=self._handle_client, args=(server,))
        self.thread.start()

    def _handle_client(self, server):
        client, _ = server.accept()

        while not self.received.endswith("\n"):
            self.received += client.recv(self.READ_CHUNK_SIZE).decode()

        client.shutdown(socket.SHUT_RDWR)

    def get_received(self) -> str:
        self.thread.join()
        return self.received


class _JobsClientTester(ProjectTestCase):
    def setUp(self):
        super().setUp()
        self.socket_path = str(Path(self.temp_dir, "jobds.sock"))

    def tearDown(self):
        self.tear_down_temp_dir()

    def setup_sock_server(self, reply):
        return SockServer(self.socket_path)


class TestCancelJobs(_JobsClientTester):
    """
    test cancel_jobs()
    """

    def test_cancel(self):
        sock_srv = self.setup_sock_server(None)

        with patch("jobs.messages.conf.JOBSD_SOCKET", self.socket_path):
            cancel_jobs(self.project.id, ["4", "34"])

        self.assertEquals(
            sock_srv.get_received(),
            '{"command": "cancel_jobs", "project_id": "1", "job_ids": ["4", "34"]}\n',
        )


class TestSubmitJobsSet(_JobsClientTester):
    """
    test submitting jobs set
    """

    def _get_db_jobs(self):
        jobs = {}
        for job in self.project.db.Job.select():
            jobs[job.description] = job

        return jobs

    @db_session
    def test_submit(self):
        sock_srv = self.setup_sock_server(None)
        jobs_set = JobsSet(self.project, "test-job-set")
        hpc_runner = get_hpc_runner()

        #
        # create a jobs set with two jobs
        #
        batch1 = hpc_runner.new_batch_file(
            "job1", "job1.sh", "job1-%j-stdout", "job1-%j-stderr", cpus=4
        )
        jobs_set.add_job(batch1)

        batch2 = hpc_runner.new_batch_file(
            "job2", "job2.sh", "job2-stdout", "job2-stderr"
        )
        jobs_set.add_job(batch2, ["arg1", "arg2"], run_after=[batch1])

        #
        # submit jobs set
        #
        with patch("jobs.messages.conf.JOBSD_SOCKET", self.socket_path):
            jobs_set.submit()

        #
        # validate
        #
        self.assertEquals(
            sock_srv.get_received(),
            '{"command": "start_jobs_set", "project_id": "1", "jobs_set_id": 1}\n',
        )

        jobs = self._get_db_jobs()

        # there should be 2 jobs created in the database
        self.assertEquals(len(jobs), 2)

        #
        # check that job1 looks correct
        #
        job = jobs["job1"]
        self.assertEquals(job.description, "job1")
        self.assertEquals(job.program, "job1.sh")
        self.assertEquals(job.get_arguments(), [])
        self.assertEquals(job.stdout, f"job1-{job.id}-stdout")
        self.assertEquals(job.stderr, f"job1-{job.id}-stderr")
        self.assertEquals(job.cpus, 4)
        self.assertEquals(job.run_on, "hpc")
        self.assertTrue(job.previous_jobs.is_empty())  # no previous jobs

        # check that next jobs is a set of 'job2'
        next_jobs = list(job.next_jobs)
        self.assertEquals(len(next_jobs), 1)
        self.assertEquals(next_jobs[0].description, "job2")

        self.assertIsNone(job.started)
        self.assertIsNone(job.finished)

        #
        # check that job2 looks correct
        #
        job = jobs["job2"]
        self.assertEquals(job.description, "job2")
        self.assertEquals(job.program, "job2.sh")
        self.assertEquals(job.get_arguments(), ["arg1", "arg2"])
        self.assertEquals(job.stdout, "job2-stdout")
        self.assertEquals(job.stderr, "job2-stderr")
        self.assertEquals(job.cpus, 0)
        self.assertEquals(job.run_on, "hpc")

        # check that next jobs is a set of 'job2'
        previous_jobs = list(job.previous_jobs)
        self.assertEquals(len(previous_jobs), 1)
        self.assertEquals(previous_jobs[0].description, "job1")

        self.assertTrue(job.next_jobs.is_empty())  # no previous jobs
        self.assertIsNone(job.started)
        self.assertIsNone(job.finished)
