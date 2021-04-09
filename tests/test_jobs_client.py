import socket
from pathlib import Path
from threading import Thread
from datetime import datetime
from unittest import TestCase
from unittest.mock import patch
from jobs.client import get_jobs
from tests.utils import TempDirMixin


class SockServer:
    READ_CHUNK_SIZE = 1024

    def __init__(self, socket_path: str, reply: str):
        self.reply = reply
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

        client.send(self.reply.encode())
        client.shutdown(socket.SHUT_RDWR)

    def get_received(self) -> str:
        self.thread.join()
        return self.received


class TestGetJobs(TestCase, TempDirMixin):
    """
    test get_jobs()
    """

    GET_JOBS_COMMAND = '{"command": "get_jobs"}\n'

    def setUp(self):
        self.setup_temp_dir()
        self.socket_path = str(Path(self.temp_dir, "jobds.sock"))

    def tearDown(self):
        self.tear_down_temp_dir()

    def setup_sock_server(self, reply):
        return SockServer(self.socket_path, reply)

    def test_no_jobs(self):
        """
        test the case when job are running
        """
        sock_srv = self.setup_sock_server('{"reply": "get_jobs", "jobs": []}')

        with patch("jobs.messages.conf.JOBSD_SOCKET", self.socket_path):
            jobs = get_jobs()

        self.assertListEqual(jobs, [])
        self.assertEquals(sock_srv.get_received(), self.GET_JOBS_COMMAND)

    def _jobs_by_id(self, jobs_list):
        jobs_dict = {}
        for job in jobs_list:
            jobs_dict[job.id] = job

        return jobs_dict

    def test_two_jobs(self):
        """
        test the case when we have one job running, and one job pending
        """
        sock_srv = self.setup_sock_server(
            '{"reply": "get_jobs", "jobs": ['
            '{"id": "42", "name": "ajob", "stdout": "stdout-42", "stderr": "stderr-42", "start_time": 0.42}, '
            '{"id": "43", "name": "pending_job", "stdout": "stdout-43", "stderr": "stderr-43"}]}'
        )

        with patch("jobs.messages.conf.JOBSD_SOCKET", self.socket_path):
            jobs = get_jobs()

        self.assertEquals(sock_srv.get_received(), self.GET_JOBS_COMMAND)

        jobs = self._jobs_by_id(jobs)

        job_42 = jobs["42"]
        self.assertEquals(job_42.name, "ajob")
        self.assertEquals(job_42.stdout, "stdout-42")
        self.assertEquals(job_42.stderr, "stderr-42")
        self.assertEquals(job_42.start_time, datetime.fromtimestamp(0.42))

        job_43 = jobs["43"]
        self.assertEquals(job_43.name, "pending_job")
        self.assertEquals(job_43.stdout, "stdout-43")
        self.assertEquals(job_43.stderr, "stderr-43")
        self.assertIsNone(job_43.start_time)
