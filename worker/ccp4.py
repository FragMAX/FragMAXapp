import subprocess
import celery
from os import path
from fragview import dist_lock


def _make_ccp4_maps(mtz_dir, mtz_file):
    fname, _ = path.splitext(mtz_file)

    if path.isfile(path.join(mtz_dir, f"{fname}_mFo-DFc.ccp4")):
        # CCP4 maps already generated
        return

    subprocess.run(["phenix.mtz2map", mtz_file], cwd=mtz_dir)


@celery.task
def mtz_to_map(mtz_dir, mtz_file):
    lock_id = f"mtz_to_map|{mtz_dir}|{mtz_file}"
    with dist_lock.acquire(lock_id):
        _make_ccp4_maps(mtz_dir, mtz_file)
