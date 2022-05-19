from typing import List, Optional
from pathlib import Path
from json import dumps, loads
from datetime import datetime
import socket
import conf


class JsonSerializable:
    def serialize(self):
        return dumps(self._as_dict())


class Job(JsonSerializable):
    def __init__(
        self,
        id,
        project_id,
        name,
        program,
        arguments,
        stdout,
        stderr,
        cpus=None,
        start_time: datetime = None,
    ):
        self.id = id
        self.project_id = project_id
        self.name = name
        self.program = program
        self.arguments = arguments
        self.stdout = stdout
        self.stderr = stderr
        self.cpus = cpus
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
            "project_id": self.project_id,
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
            project_id=d["project_id"],
            name=d["name"],
            program=None,
            arguments=[],
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

    def __init__(self, project_id: Optional[str]):
        self.project_id = project_id

    def _as_dict(self):
        d = {
            "command": self.LABEL,
        }
        if self.project_id:
            d["project_id"] = str(self.project_id)

        return d

    @staticmethod
    def from_dict(d):
        return GetJobs(d.get("project_id"))


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

    def __init__(self, project_id, name: str, jobs: List[dict]):
        self.project_id = project_id
        self.name = name
        self.jobs = jobs

    def _as_dict(self):
        return {
            "command": self.LABEL,
            "jobs_set": {
                "project_id": self.project_id,
                "name": self.name,
                "jobs": self.jobs,
            },
        }

    @staticmethod
    def from_dict(json_dict):
        jobs_set = json_dict["jobs_set"]
        return StartJobs(jobs_set["project_id"], jobs_set["name"], jobs_set["jobs"])


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


def post_start_jobs_command(project_id, name, jobs):
    _send_command(StartJobs(project_id, name, jobs))


def post_cancel_jobs_command(job_ids):
    _send_command(CancelJobs(job_ids))


def post_get_jobs_command(project_id: Optional[str]):
    return _send_command(GetJobs(project_id))
