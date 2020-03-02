import celery
from os import path
from worker import dist_lock
from fragview import hpc, versions


def _make_rlp_json(data_dir):
    rlp_path = path.join(data_dir, "rlp.json")

    if path.isfile(rlp_path):
        # rlp.json already generated
        return

    cmd = \
        f"cd {data_dir};" + \
        f"module load {versions.DIALS_MOD};" + \
        "dials.export 2_SWEEP1_strong.refl 2_SWEEP1_strong.expt format=json"

    hpc.frontend_run(cmd)


@celery.task
def get_rlp(data_dir):
    lock_id = f"get_rlp|{data_dir}"

    with dist_lock.acquire(lock_id):
        _make_rlp_json(data_dir)
