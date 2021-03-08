import sys
import subprocess
from typing import Dict, List
from datetime import datetime
from pathlib import Path
from django.conf import settings
from fragview.sites import SITE
from jobs import client


def _ssh_on_frontend(command):
    """
    return a tuple of (stdout, stderr, exit_code)
    """
    print(f"running on HPC '{command}'")
    with subprocess.Popen(
        ["ssh", settings.HPC_FRONT_END], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    ) as proc:

        stdout, stderr = proc.communicate(command.encode("utf-8"))
        return stdout, stderr, proc.returncode


def _forward_output(output, stream):
    if output is None:
        # no output to forward
        return

    if not hasattr(stream, "buffer"):
        stream.write(output)
        return

    stream.buffer.write(output)


def frontend_run(command, forward=True):
    """
    run shell command on HPC front-end host,
    the shell command's stdout and stderr will be dumped to our stdout and stderr streams
    """

    # TODO: check exit code and bubble up error on exit code != 0
    stdout, stderr, _ = _ssh_on_frontend(command)

    if forward:
        # forward stdout and stderr outputs, for traceability
        _forward_output(stdout, sys.stdout)
        _forward_output(stderr, sys.stderr)
    else:
        return stdout, stderr


def _elapsed_time(start: datetime, end: datetime) -> Dict[str, int]:
    """
    calculate time elapsed from start to end time,
    returns elapsed time divided into hours, minutes and seconds
    """
    delta = end - start

    # let's use seconds precision
    seconds_delta = delta.seconds

    seconds = seconds_delta % 60
    minutes = (seconds_delta // 60) % 60
    hours = seconds_delta // 3600

    return dict(hours=hours, minutes=minutes, seconds=seconds)


def get_jobs() -> List[Dict]:
    def _run_time(start_time):
        if start_time is None:
            return None

        return _elapsed_time(start_time, now)

    now = datetime.now()

    #
    # convert Jobs table into a format that is more
    # convenient for presenting to the user
    #
    jobs = []
    for job in client.get_jobs():
        jobs.append(
            dict(
                id=job.id,
                name=job.name,
                stdout=Path(job.stdout).name,
                stderr=Path(job.stderr).name,
                run_time=_run_time(job.start_time),
            )
        )

    return jobs


def cancel_jobs(job_ids):
    client.cancel_jobs(job_ids)


def run_sbatch(sbatch_script, sbatch_options=None):
    SITE.get_hpc_runner().run_batch(sbatch_script, sbatch_options)
