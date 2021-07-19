from typing import List
from fragview import dist_lock
import subprocess
import celery


def _command_hash(command: List[str]):
    return hash("".join(command))


@celery.task
def make_diffraction_jpeg(command: List[str]):
    lock_id = f"make_diffraction_jpeg|{_command_hash(command)}"
    with dist_lock.acquire(lock_id):
        subprocess.run(command)
