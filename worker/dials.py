import celery
from os import path
from fragview import hpc, versions, dist_lock
from glob import glob


def _make_rlp_json(data_dir):
    rlp_path = path.join(data_dir, "rlp.json")

    if path.isfile(rlp_path):
        # rlp.json already generated
        return
    refl = sorted(glob(f"{data_dir}/*indexed*refl"))
    expt = sorted(glob(f"{data_dir}/*indexed*expt"))
    if refl and expt:
        refl, expt = refl[-1], expt[-1]
    cmd = (
        f"cd {data_dir};"
        + f"module load gopresto {versions.DIALS_MOD};"
        + f"dials.export {refl} {expt} format=json"
    )

    hpc.frontend_run(cmd)


@celery.task
def get_rlp(data_dir):
    lock_id = f"get_rlp|{data_dir}"

    with dist_lock.acquire(lock_id):
        _make_rlp_json(data_dir)
