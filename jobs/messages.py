from json import dumps, loads
import socket
import conf


class JsonSerializable:
    def serialize(self):
        return dumps(self._as_dict())


class StartJobsSet(JsonSerializable):
    LABEL = "start_jobs_set"

    def __init__(self, project_id: str, jobs_set_id: str):
        self.project_id = project_id
        self.jobs_set_id = jobs_set_id

    def _as_dict(self):
        return {
            "command": self.LABEL,
            "project_id": self.project_id,
            "jobs_set_id": self.jobs_set_id,
        }

    @staticmethod
    def from_dict(json_dict):
        return StartJobsSet(json_dict["project_id"], json_dict["jobs_set_id"])


class CancelJobs(JsonSerializable):
    LABEL = "cancel_jobs"

    def __init__(self, project_id, job_ids):
        self.project_id = project_id
        self.job_ids = job_ids

    def _as_dict(self):
        return {
            "command": self.LABEL,
            "project_id": self.project_id,
            "job_ids": self.job_ids,
        }

    @staticmethod
    def from_dict(json_dict):
        return CancelJobs(json_dict["project_id"], json_dict["job_ids"])

    def __str__(self):
        return f"CancelJobs: job_ids '{self.job_ids}'"


def deserialize_command(data):
    json_dict = loads(data.decode())

    cmd_label = json_dict["command"]
    if cmd_label == StartJobsSet.LABEL:
        return StartJobsSet.from_dict(json_dict)
    if cmd_label == CancelJobs.LABEL:
        return CancelJobs.from_dict(json_dict)

    raise ValueError(f"unknown command {cmd_label}")


def _open_socket():
    client = socket.socket(socket.AF_UNIX)
    client.connect(conf.JOBSD_SOCKET)

    return client.makefile("rw")


def _send_command(command):
    sock = _open_socket()
    cmd_data = command.serialize() + "\n"
    sock.write(cmd_data)
    sock.flush()
    sock.close()


def post_start_jobs_set_command(project_id, jobs_set_id):
    _send_command(StartJobsSet(project_id, jobs_set_id))


def post_cancel_jobs_command(project_id: str, job_ids: list[str]):
    _send_command(CancelJobs(project_id, job_ids))
