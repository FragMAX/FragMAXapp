import subprocess
from django.conf import settings


def _hpc_user(logged_in_user):
    if settings.HPC_USER is None:
        return logged_in_user.username

    return settings.HPC_USER


def jobs_list(logged_in_user):
    user = _hpc_user(logged_in_user)

    command = ["ssh", "-t", settings.HPC_FRONT_END, "squeue", "-u", user]

    print(f"running {command}")

    proc = subprocess.Popen(command,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE)

    out, _ = proc.communicate()

    return out
