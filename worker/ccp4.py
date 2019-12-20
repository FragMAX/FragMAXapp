import subprocess
import celery
from os import path
from worker import dist_lock


def _make_ccp4_maps(mtz_dir):
    if path.isfile(path.join(mtz_dir, "final_mFo-DFc.ccp4")):
        # CCP4 maps already generated
        return

    subprocess.run(["phenix.mtz2map", "final.mtz"], cwd=mtz_dir)


@celery.task
def mtz_to_map(mtz_dir):
    lock_id = f"mtz_to_map|{mtz_dir}"
    with dist_lock.acquire(lock_id):
        _make_ccp4_maps(mtz_dir)
