from os import path
from glob import glob
from celery.utils.log import get_task_logger
from fragview.fileio import makedirs
from fragview.projects import project_datasets, project_script, project_process_protein_dir, shifts_raw_master_h5_files
from fragmax import sites
from fragview import hpc


logger = get_task_logger(__name__)


def _setup_plain_folders(project, _):
    root_dir = project_process_protein_dir(project)

    for dataset in project_datasets(project):
        dataset_dir, _ = dataset.rsplit("_", 2)
        makedirs(path.join(root_dir, dataset_dir, dataset))


def import_edna_fastdp(proj, shifts):
    # Copy data from beamline auto processing to fragmax folders
    # Should be run in a different thread
    h5s = list(shifts_raw_master_h5_files(proj, shifts))

    logger.info(f"importing EDNA/fast_dp results for {len(h5s)} datasets")
    num_of_datasets = len(h5s)

    for set_num, h5 in zip(range(num_of_datasets), h5s):
        dataset, run = (h5.split("/")[-1][:-10].split("_"))

        logger.info(f"importing {dataset}-{run} ({set_num + 1}/{num_of_datasets}) results")

        shift_collection = h5.split("/")[5]
        edna_path_src = f"/data/visitors/biomax/{proj.proposal}/{shift_collection}/process/{proj.protein}/"\
            f"{dataset}/xds_{dataset}_{run}_1/EDNA_proc/results/"
        edna_path_dst = f"{proj.data_path()}/fragmax/process/{proj.protein}/{dataset}/{dataset}_{run}/edna/"

        fastdp_path_src = f"/data/visitors/biomax/{proj.proposal}/{shift_collection}/process/{proj.protein}"\
            f"/{dataset}/xds_{dataset}_{run}_1/fastdp/results/"
        fastdp_path_dst = f"{proj.data_path()}/fragmax/process/{proj.protein}/{dataset}/{dataset}_{run}/fastdp/"

        autoproc_path_src = glob(f"/data/visitors/biomax/{proj.proposal}/{shift_collection}/process/{proj.protein}"
                                 f"/{dataset}/xds_{dataset}_{run}_1/autoPROC/cn*/AutoPROCv1_0_anom/")
        autoproc_path_dst = f"{proj.data_path()}/fragmax/process/{proj.protein}/{dataset}/{dataset}_{run}/autoproc/"

        script = project_script(proj, f"import_edna_fastdp.sh")

        if path.exists(edna_path_src):
            if not path.exists(edna_path_dst):
                logger.info("importing EDNA results")
                with open(script, "w") as outfile:
                    outfile.write("#!/bin/bash\n")
                    outfile.write("#!/bin/bash\n")
                    outfile.write("module purge\n")
                    outfile.write(f"mkdir -p {edna_path_dst}\n")
                    outfile.write(f"rsync -r {edna_path_src} {edna_path_dst}\n")
                hpc.run_sbatch(script)

        if path.exists(fastdp_path_src):
            if not path.exists(fastdp_path_dst):
                logger.info("importing fast_dp results")
                with open(script, "w") as outfile:
                    outfile.write("#!/bin/bash\n")
                    outfile.write("#!/bin/bash\n")
                    outfile.write("module purge\n")
                    outfile.write(f"mkdir -p {fastdp_path_dst}\n")
                    outfile.write(f"rsync -r {fastdp_path_src} {fastdp_path_dst}\n")
                    outfile.write(f"gzip -d {fastdp_path_dst}*gz\n")
                hpc.run_sbatch(script)

        if autoproc_path_src:
            autoproc_path_src = autoproc_path_src[0]
            if path.exists(autoproc_path_src):
                if not path.exists(autoproc_path_dst):
                    logger.info("importing autoPROC results")
                    with open(script, "w") as outfile:
                        outfile.write("#!/bin/bash\n")
                        outfile.write("#!/bin/bash\n")
                        outfile.write("module purge\n")
                        outfile.write(f"mkdir -p {autoproc_path_dst}\n")
                        outfile.write(f"rsync -r {autoproc_path_src} {autoproc_path_dst}\n")
                        outfile.write(f"cd {autoproc_path_dst}\n")
                        outfile.write(f"mv {autoproc_path_dst}HDF5_1/* {autoproc_path_dst}\n")

                    hpc.run_sbatch(script)


def _setup_shifts_folders(project, shifts):
    import_edna_fastdp(project, shifts)


_DATA_LAYOUT_FUNCS = {
    "shifts": _setup_shifts_folders,
    "plain": _setup_plain_folders,
}


def _prepare_function():
    """
    pick project folders prepare function for the configured data layout
    """
    style = sites.params().DATA_LAYOUT
    return _DATA_LAYOUT_FUNCS[style]


def prepare_project_folders(project, shifts):
    func = _prepare_function()
    func(project, shifts)
