from os import path
from fragview import dist_lock
import subprocess
import celery
from fragview.sites import SITE


def _make_diffraction_image(source_file, dest_pic_file):
    if path.exists(dest_pic_file):
        # diffraction picture already generated
        return

    image_maker = SITE.get_diffraction_img_maker()
    cmd = image_maker.get_command(source_file, dest_pic_file)
    subprocess.run(cmd)


@celery.task
def get_diffraction(source_file, dest_pic_file):
    """
    generate diffraction picture from the specified H5 source file
    """
    lock_id = f"get_diffraction|{dest_pic_file}"
    with dist_lock.acquire(lock_id):
        _make_diffraction_image(source_file, dest_pic_file)
