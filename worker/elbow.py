from os import path
import queue
import shutil
import threading
# import subprocess
from fragview import hpc

NUM_WORKERS = 3


class SmilesFragsMap:
    def __init__(self):
        self._map = dict()

    def add_fragment(self, smiles, fragment):
        if smiles in self._map:
            # existing SMILES
            self._map[smiles].append(fragment)
            return

        # new SMILES
        self._map[smiles] = [fragment]

    def get_items(self):
        return self._map.items()


def generate_cif_pdb(fragments, dest_dir):
    sf_map = SmilesFragsMap()
    for frag in fragments:
        sf_map.add_fragment(frag.smiles, frag.name)

    work_queue = queue.Queue()
    for smiles_frags in sf_map.get_items():
        work_queue.put(smiles_frags)

    threads = []
    for _ in range(NUM_WORKERS):
        t = threading.Thread(target=_worker, args=(work_queue, dest_dir))
        t.start()
        threads.append(t)

    for t in threads:
        t.join()


def _worker(work_queue, dest_dir):
    try:
        while True:
            smiles, frags = work_queue.get_nowait()
            _run_elbow(smiles, frags, dest_dir)
    except queue.Empty:
        # no more fragments to process
        pass


def _file_names(frag_name, dest_dir):
    cif = path.join(dest_dir, f"{frag_name}.cif")
    pdb = path.join(dest_dir, f"{frag_name}.pdb")

    return cif, pdb


def _run_elbow(smiles, fragments, dest_dir):
    first_frag, *rest_frags = fragments

    print(f"{smiles} => {first_frag}")
    script_dir = path.join(path.dirname(dest_dir), "scripts")
    script = path.join(script_dir, f"elbow.sh")
    with open(script, "w") as outfile:
        outfile.write("#!/bin/bash\n")
        outfile.write("#!/bin/bash\n")
        outfile.write("module purge\n")
        outfile.write("module load Phenix\n")
        outfile.write(f"cd {dest_dir}\n")
        outfile.write(f"phenix.elbow --smiles={smiles} --output={first_frag}\n")
    hpc.run_sbatch(script)

    src_cif, src_pdb = _file_names(first_frag, dest_dir)

    for frag in rest_frags:
        dst_cif, dst_pdb = _file_names(frag, dest_dir)

        print(f"{src_cif} -> {dst_cif}")
        shutil.copy(src_cif, dst_cif)

        shutil.copy(src_pdb, dst_pdb)
        print(f"{src_pdb} -> {dst_pdb}")


def _run_acedrg(smiles, fragments, dest_dir):
    first_frag, *rest_frags = fragments

    print(f"{smiles} => {first_frag}")

    script_dir = path.join(path.dirname(dest_dir), "scripts")
    script = path.join(script_dir, f"elbow.sh")
    with open(script, "w") as outfile:
        outfile.write("#!/bin/bash\n")
        outfile.write("#!/bin/bash\n")
        outfile.write("module purge\n")
        outfile.write("module load CCP4\n")
        outfile.write(f"cd {dest_dir}\n")
        outfile.write(f"acedrg -i '{smiles}' -o {first_frag}\n")
    hpc.run_sbatch(script)

    src_cif, src_pdb = _file_names(first_frag, dest_dir)

    for frag in rest_frags:
        dst_cif, dst_pdb = _file_names(frag, dest_dir)

        print(f"{src_cif} -> {dst_cif}")
        shutil.copy(src_cif, dst_cif)

        shutil.copy(src_pdb, dst_pdb)
        print(f"{src_pdb} -> {dst_pdb}"