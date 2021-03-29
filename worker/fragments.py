import celery
import subprocess
from pathlib import Path
from fragview import dist_lock


def _make_pdb(smiles, frag_dir, frag_name):
    pdb_path = Path(frag_dir, f"{frag_name}.pdb")

    if pdb_path.is_file():
        # PDB already exists
        return

    subprocess.run(
        ["phenix.elbow", f"--smiles={smiles}", f"--output={frag_name}"], cwd=frag_dir
    )


@celery.task
def smiles_to_pdb(smiles, frag_dir, frag_name):
    lock_id = f"smiles_to_pdb|{smiles}|{frag_dir}|{frag_name}"
    with dist_lock.acquire(lock_id):
        _make_pdb(smiles, frag_dir, frag_name)
