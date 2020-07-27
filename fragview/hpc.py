import sys
import subprocess
from django.conf import settings
from fragview.sites import SITE


def _hpc_user(logged_in_user):
    if settings.HPC_USER is None:
        return logged_in_user.username

    return settings.HPC_USER


def _ssh_on_frontend(command):
    """
    return a tuple of (stdout, stderr, exit_code)
    """
    print(f"running on HPC '{command}'")
    with subprocess.Popen(["ssh", settings.HPC_FRONT_END],
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE) as proc:

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


def jobs_list(logged_in_user):
    user = _hpc_user(logged_in_user)

    command = ["ssh", "-t", settings.HPC_FRONT_END, "squeue", "-u", user]

    proc = subprocess.Popen(command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out, _ = proc.communicate()

    return out


def run_sbatch(sbatch_script, sbatch_options=None):
    SITE.get_hpc_runner().run_batch(sbatch_script, sbatch_options)
