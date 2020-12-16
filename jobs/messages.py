from typing import List
from pathlib import Path
from json import dumps, loads
from datetime import datetime
import socket
import conf


class JsonSerializable:
    def serialize(self):
        return dumps(self._as_dict())


class Job(JsonSerializable):
    def __init__(self, id, name, program, stdout, stderr, start_time: datetime = None):
        self.id = id
        self.name = name
        self.program = program
        self.stdout = stdout
        self.stderr = stderr
        # None start_time for jobs in pending state
        self.start_time = start_time

    def mark_as_started(self):
        """
        set this jobs 'start time' to now,
        thus changing it's state from 'pending' to 'running'
        """
        self.start_time = datetime.now()

    def _as_dict(self):
        d = {
            "id": self.id,
            "name": self.name,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }
        if self.start_time is not None:
            d["start_time"] = self.start_time.timestamp()

        return d

    @staticmethod
    def from_dict(d):
        start_time = d.get("start_time")
        if start_time is not None:
            start_time = datetime.fromtimestamp(float(start_time))

        return Job(
            id=d["id"],
            name=d["name"],
            program=None,
            stdout=d["stdout"],
            stderr=d["stderr"],
            start_time=start_time,
        )

    def stdout_filename(self):
        """
        the job's stdout logs file name, rather then full path
        """
        return Path(self.stdout).name

    def stderr_filename(self):
        """
        the job's stdout logs file name, rather then full path
        """
        return Path(self.stderr).name

    def __str__(self):
        return f"Job: name '{self.name}'"


class GetJobs(JsonSerializable):
    LABEL = "get_jobs"

    def _as_dict(self):
        return {
            "command": self.LABEL,
        }

    @staticmethod
    def from_dict(_):
        return GetJobs()


class GetJobsReply(JsonSerializable):
    LABEL = GetJobs.LABEL

    def __init__(self):
        self.jobs = []

    def add_job(self, job):
        self.jobs.append(job)

    def _as_dict(self):
        return {"reply": self.LABEL, "jobs": [job._as_dict() for job in self.jobs]}

    @staticmethod
    def from_dict(json_dict):
        jobs_list = json_dict["jobs"]

        reply = GetJobsReply()
        reply.jobs = [Job.from_dict(job_dict) for job_dict in jobs_list]

        return reply


class StartJobs(JsonSerializable):
    LABEL = "start_jobs"

    def __init__(self, name, jobs: List[dict]):
        self.name = name
        self.jobs = jobs

    def _as_dict(self):
        return {
            "command": self.LABEL,
            "jobs_set": {"name": self.name, "jobs": self.jobs},
        }

    @staticmethod
    def from_dict(json_dict):
        jobs_set = json_dict["jobs_set"]
        return StartJobs(jobs_set["name"], jobs_set["jobs"])


class CancelJobs(JsonSerializable):
    LABEL = "cancel_jobs"

    def __init__(self, job_ids):
        self.job_ids = job_ids

    def _as_dict(self):
        return {
            "command": self.LABEL,
            "job_ids": self.job_ids,
        }

    @staticmethod
    def from_dict(json_dict):
        return CancelJobs(json_dict["job_ids"])

    def __str__(self):
        return f"CancelJobs: job_ids '{self.job_ids}'"


def deserialize_command(data):
    json_dict = loads(data.decode())

    cmd_label = json_dict["command"]
    if cmd_label == GetJobs.LABEL:
        return GetJobs.from_dict(json_dict)
    if cmd_label == StartJobs.LABEL:
        return StartJobs.from_dict(json_dict)
    if cmd_label == CancelJobs.LABEL:
        return CancelJobs.from_dict(json_dict)

    raise ValueError(f"unknown command {cmd_label}")


def deserialize_reply(text):
    json_dict = loads(text)

    reply_label = json_dict["reply"]
    if reply_label == GetJobsReply.LABEL:
        return GetJobsReply.from_dict(json_dict)

    raise ValueError(f"unknown reply {reply_label}")


def _open_socket():
    client = socket.socket(socket.AF_UNIX)
    client.connect(conf.JOBSD_SOCKET)

    return client.makefile("rw")


def _send_command(command):
    sock = _open_socket()
    cmd_data = command.serialize() + "\n"
    sock.write(cmd_data)
    sock.flush()

    reply = sock.readline()
    sock.close()

    if reply:
        return deserialize_reply(reply)


def post_start_jobs_command(name, jobs):
    _send_command(StartJobs(name, jobs))


def post_cancel_jobs_command(job_ids):
    _send_command(CancelJobs(job_ids))


def post_get_jobs_command():
    return _send_command(GetJobs())
