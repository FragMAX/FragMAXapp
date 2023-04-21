import subprocess
import celery
from fragview import dist_lock


def _command_hash(command: list[str]):
    return hash("".join(command))


@celery.shared_task
def make_diffraction_jpeg(command: list[str]):
    lock_id = f"make_diffraction_jpeg|{_command_hash(command)}"
    with dist_lock.acquire(lock_id):
        subprocess.run(command)
