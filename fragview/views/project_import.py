import os
from glob import glob
import pyfastcopy  # noqa
import shutil
import subprocess
import itertools


def import_edna_fastdp(proj):
    # Copy data from beamline auto processing to fragmax folders
    # Should be run in a different thread
    h5s = list(itertools.chain(
        *[glob(f"/data/visitors/biomax/{proj.proposal}/{shift}/raw/{proj.protein}/"
               f"{proj.protein}*/{proj.protein}*master.h5")
            for shift in proj.shifts()])
    )
    for h5 in h5s:
        dataset, run = (h5.split("/")[-1][:-10].split("_"))
        shift_collection = h5.split("/")[5]
        edna_path_src = f"/data/visitors/biomax/{proj.proposal}/{shift_collection}/process/{proj.protein}/"\
            f"{dataset}/xds_{dataset}_{run}_1/EDNA_proc/results/"
        edna_path_dst = f"{proj.data_path()}/fragmax/process/{proj.protein}/{dataset}/{dataset}_{run}/edna/"
        fastdp_path_src = f"/data/visitors/biomax/{proj.proposal}/{shift_collection}/process/{proj.protein}"\
            f"/{dataset}/xds_{dataset}_{run}_1/fastdp/results/"
        fastdp_path_dst = f"{proj.data_path()}/fragmax/process/{proj.protein}/{dataset}/{dataset}_{run}/fastdp/"

        if os.path.exists(edna_path_src):
            if not os.path.exists(edna_path_dst):
                shutil.copytree(edna_path_src, edna_path_dst)

        if os.path.exists(fastdp_path_src):
            if not os.path.exists(fastdp_path_dst):
                shutil.copytree(fastdp_path_src, fastdp_path_dst)
                subprocess.call(f"gzip -d {fastdp_path_dst}/*gz", shell=True)
