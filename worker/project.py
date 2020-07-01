import os
from os import path
import grp
import csv
import stat
from glob import glob
import pyfastcopy  # noqa
import shutil
import xmltodict
import subprocess
from pathlib import Path
import celery
from celery.utils.log import get_task_logger
from worker import dist_lock, elbow
from fragview.models import Project
from fragview.projects import proposal_dir, project_xml_files, project_process_protein_dir
from fragview.projects import project_data_collections_file, project_fragmax_dir
from fragview.projects import project_shift_dirs, project_all_status_file, project_fragments_dir
from fragview.projects import shifts_xml_files, shifts_raw_master_h5_files, project_scripts_dir
from fragview.projects import UPDATE_STATUS_SCRIPT, PANDDA_WORKER

logger = get_task_logger(__name__)


@celery.task
def setup_project_files(proj_id):
    try:
        proj = Project.get(proj_id)
    except Project.DoesNotExist:
        logger.warning(f"warning: no project with ID {proj_id}, will not setup it's files")
        return

    with dist_lock.acquire(f"setup_project_files|{proj_id}"):
        logger.info(f"setup project {proj.protein}-{proj.library.name} ({proj.id})")
        _setup_project_files(proj)
        proj.set_ready()


@celery.task
def add_new_shifts(proj_id, shifts):
    try:
        proj = Project.get(proj_id)
    except Project.DoesNotExist:
        logger.warning(f"warning: no project with ID {proj_id}, will add new shift(s)")
        return

    with dist_lock.acquire(f"add_new_shifts|{proj_id}"):
        logger.info(f"import new shifts {shifts} to {proj.protein}-{proj.library.name} ({proj.id})")
        _add_new_shifts_files(proj, shifts)
        proj.set_ready()


def _add_new_shifts_files(proj, shifts):
    meta_files = list(shifts_xml_files(proj, shifts))
    _copy_collection_metadata_files(proj, meta_files)
    _write_data_collections_file(proj, project_xml_files(proj))
    _import_edna_fastdp(proj, shifts)
    _write_project_status(proj)


def _setup_project_files(proj):
    meta_files = list(project_xml_files(proj))
    _create_fragmax_folders(proj)
    _prepare_fragments(proj)
    _copy_scripts(proj)
    _copy_collection_metadata_files(proj, meta_files)
    _write_data_collections_file(proj, meta_files)
    _import_edna_fastdp(proj, proj.shifts())
    _write_project_status(proj)


def _makedirs(dir_path):
    os.makedirs(dir_path, mode=0o770, exist_ok=True)


def _prepare_fragments(proj):
    frags_dir = project_fragments_dir(proj)
    lib = proj.library

    elbow.generate_cif_pdb(lib.fragment_set.all(), frags_dir)


def _make_fragmax_dir(proj):
    """
    create the 'fragmax' directory and make sure it:

      - it's owner group is set to the proposal group
      - the SETGID bit is set

    this ownership and permission makes all the files created under
    the fragmax folder accessible to all users in the proposal group
    """
    fragmax_dir = project_fragmax_dir(proj)
    if path.exists(fragmax_dir):
        # directory already exists,
        # which can happen when different proteins are collected during same shift,
        # and we create two different project which end up sharing 'main shift' folder
        # let's hope the owner group and SETGID are correct
        return fragmax_dir

    # look-up proposal group ID
    proposal_group = grp.getgrnam(f"{proj.proposal}-group")

    os.mkdir(fragmax_dir)
    # set owner group
    os.chown(fragmax_dir, -1, proposal_group.gr_gid)
    # make sure SETGID bit is set
    os.chmod(fragmax_dir,
             stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR |
             stat.S_ISGID | stat.S_IRGRP | stat.S_IWGRP | stat.S_IXGRP)

    return fragmax_dir


def _create_fragmax_folders(proj):
    """
    create folders that fragmax will use for dataprocessing
    """
    fragmax_dir = _make_fragmax_dir(proj)

    _makedirs(path.join(fragmax_dir, "logs"))
    _makedirs(path.join(fragmax_dir, "scripts"))
    _makedirs(path.join(fragmax_dir, "models"))
    _makedirs(path.join(fragmax_dir, "export"))
    _makedirs(path.join(fragmax_dir, "results"))
    _makedirs(project_fragments_dir(proj))
    _makedirs(project_process_protein_dir(proj))


def _copy_script_files(proj, script_files):
    data_dir = path.join(path.dirname(__file__), "data")
    dest_dir = project_scripts_dir(proj)

    for file in script_files:
        src_file = path.join(data_dir, file)
        dst_file = path.join(dest_dir, file)
        print(f"{src_file} -> {dst_file}")
        shutil.copy(src_file, dst_file)


def _copy_scripts(proj):
    script_files = [UPDATE_STATUS_SCRIPT, PANDDA_WORKER]
    if proj.encrypted:
        script_files += ["crypt_files.py", "crypt_files.sh"]

    _copy_script_files(proj, script_files)


def _parse_metafile(proj, metafile):
    def _snapshots():
        for i in range(1, 5):
            snap = node[f"xtalSnapshotFullPath{i}"]
            if snap != "None":
                yield snap

    with open(metafile, "rb") as f:
        doc = xmltodict.parse(f)

    node = doc["XSDataResultRetrieveDataCollection"]["dataCollection"]

    img_num = node["numberOfImages"]
    resolution = "%.2f" % float(node["resolution"])
    run = node["dataCollectionNumber"]
    dataset = node["imagePrefix"]
    sample = dataset.split("-")[-1]
    snaps = ",".join(_snapshots())
    # TODO remove this if expression, change the code to use empty string works as 'no snapshots' value
    if len(snaps) <= 0:
        snaps = "noSnapshots"
    col_path = node["imageDirectory"]

    return dataset, sample, col_path, run, img_num, resolution, snaps


def _write_data_collections_file(proj, meta_files):
    dc_file = project_data_collections_file(proj)
    logger.info(f"writing {dc_file}")

    with open(dc_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow([
            "imagePrefix", "SampleName", "dataCollectionPath", "Acronym", "dataCollectionNumber",
            "numberOfImages", "resolution", "snapshot"])

        for mfile in meta_files:
            dataset, sample, col_path, run, img_num, resolution, snaps = _parse_metafile(proj, mfile)
            writer.writerow([dataset, sample, col_path, proj.protein, run, img_num, resolution, snaps])


def _copy_collection_metadata_files(proj, meta_files):
    def _sample_shift_name(meta_file_path):
        path_parts = Path(meta_file_path).parts
        samle = path_parts[prop_dir_depth + 4][4:-2]

        return path_parts[prop_dir_depth + 3], f"{samle}.xml"

    prop_dir = proposal_dir(proj.proposal)
    prop_dir_depth = len(Path(prop_dir).parts)
    proto_dir = project_process_protein_dir(proj)

    for mfile in meta_files:
        sample_dir, sample_filename = _sample_shift_name(mfile)

        dest_dir = path.join(proto_dir, sample_dir)
        dest_file = path.join(dest_dir, sample_filename)

        _makedirs(dest_dir)
        shutil.copyfile(mfile, dest_file)


def _import_edna_fastdp(proj, shifts):
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

        if path.exists(edna_path_src):
            if not path.exists(edna_path_dst):
                logger.info("importing EDNA results")
                shutil.copytree(edna_path_src, edna_path_dst)

        if path.exists(fastdp_path_src):
            if not path.exists(fastdp_path_dst):
                logger.info("importing fast_dp results")
                shutil.copytree(fastdp_path_src, fastdp_path_dst)
                subprocess.call(f"gzip -d {fastdp_path_dst}/*gz", shell=True)


def _write_project_status(proj):
    logger.info("writing project status")

    statusDict = dict()
    procList = list()
    resList = list()

    for shift_dir in project_shift_dirs(proj):
        procList += [
            "/".join(x.split("/")[:8]) + "/" + x.split("/")[-2] + "/" for x in
            glob(f"{shift_dir}/fragmax/process/{proj.protein}/*/*/")]
        resList += glob(f"{shift_dir}/fragmax/results/{proj.protein}*/")

    for i in procList:
        dataset_run = i.split("/")[-2]
        statusDict[dataset_run] = {
            "autoproc": "none",
            "dials": "none",
            "EDNA": "none",
            "fastdp": "none",
            "xdsapp": "none",
            "xdsxscale": "none",
            "dimple": "none",
            "fspipeline": "none",
            "buster": "none",
            "rhofit": "none",
            "ligfit": "none",
        }

    for result in resList:
        dts = result.split("/")[-2]
        if dts not in statusDict:
            statusDict[dts] = {
                "autoproc": "none",
                "dials": "none",
                "EDNA": "none",
                "fastdp": "none",
                "xdsapp": "none",
                "xdsxscale": "none",
                "dimple": "none",
                "fspipeline": "none",
                "buster": "none",
                "rhofit": "none",
                "ligfit": "none",
            }

        for j in glob(result + "*"):
            if os.path.exists(j + "/dimple/final.pdb"):
                statusDict[dts].update({"dimple": "full"})

            if os.path.exists(j + "/fspipeline/final.pdb"):
                statusDict[dts].update({"fspipeline": "full"})

            if os.path.exists(j + "/buster/final.pdb"):
                statusDict[dts].update({"buster": "full"})

            if glob(j + "/*/ligfit/LigandFit*/ligand_fit_*.pdb") != []:
                statusDict[dts].update({"ligfit": "full"})

            if glob(j + "/*/rhofit/best.pdb") != []:
                statusDict[dts].update({"rhofit": "full"})

    for process in procList:
        dts = process.split("/")[-2]
        j = list()

        for shift_dir in project_shift_dirs(proj):
            j += glob(f"{shift_dir}/fragmax/process/{proj.protein}/*/{dts}/")

        if j != []:
            j = j[0]

        if glob(j + "/autoproc/*staraniso*.mtz") + glob(j + "/autoproc/*aimless*.mtz") != []:
            statusDict[dts].update({"autoproc": "full"})

        if glob(j + "/dials/DataFiles/*mtz") != []:
            statusDict[dts].update({"dials": "full"})

        ej = list()
        for shift_dir in project_shift_dirs(proj):
            ej += glob(f"{shift_dir}/process/{proj.protein}/*/*{dts}*/EDNA_proc/results/*mtz")

        if ej != []:
            statusDict[dts].update({"EDNA": "full"})
        fj = list()

        for shift_dir in project_shift_dirs(proj):
            fj += glob(f"{shift_dir}/process/{proj.protein}/*/*{dts}*/fastdp/results/*mtz.gz")

        if fj != []:
            statusDict[dts].update({"fastdp": "full"})

        if glob(j + "/xdsapp/*mtz") != []:
            statusDict[dts].update({"xdsapp": "full"})

        if glob(j + "/xdsxscale/DataFiles/*mtz") != []:
            statusDict[dts].update({"xdsxscale": "full"})

    with open(project_all_status_file(proj), "w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["dataset_run", "autoproc", "dials", "EDNA", "fastdp", "xdsapp",
                         "xdsxscale", "dimple", "fspipeline", "buster", "ligfit", "rhofit"])
        for dataset_run, status in statusDict.items():
            writer.writerow([dataset_run] + list(status.values()))
