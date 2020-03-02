from os import path
from worker import dist_lock
import subprocess
import celery


def _make_diffraction_image(h5_source_file, dest_pic_file):
    if path.exists(dest_pic_file):
        # diffraction picture already generated
        return

    cmd = ["adxv", "-sa", "-slabs", "10", "-weak_data", h5_source_file,  dest_pic_file]
    subprocess.run(cmd)


@celery.task
def get_diffraction(h5_source_file, dest_pic_file):
    """
    generate diffraction picture from the specified H5 source file
    """
    lock_id = f"get_diffraction|{dest_pic_file}"
    with dist_lock.acquire(lock_id):
        _make_diffraction_image(h5_source_file, dest_pic_file)
