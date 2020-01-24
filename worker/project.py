import os
from os import path
import csv
from glob import glob
import pyfastcopy  # noqa
import shutil
import itertools
import xmltodict
import subprocess
from pathlib import Path
import celery
from celery.utils.log import get_task_logger
from worker import dist_lock
from fragview.models import Project
from fragview.projects import proposal_dir, project_xml_files, project_static_url, project_process_protein_dir
from fragview.projects import UPDATE_STATUS_SCRIPT, project_update_status_script

logger = get_task_logger(__name__)


@celery.task
def setup_project_files(proj_id):
    try:
        proj = Project.get(proj_id)
    except Project.DoesNotExist:
        logger.warning(f"warning: no project with ID {proj_id}, will not setup it's files")
        return

    with dist_lock.acquire(f"setup_project_files|{proj_id}"):
        logger.info(f"setup project {proj.protein}-{proj.library} ({proj.id})")
        _setup_project_files(proj)
        proj.set_ready()


def _setup_project_files(proj):
    meta_files = list(project_xml_files(proj))
    _create_fragmax_folders(proj)
    _write_update_script(proj)
    _copy_collection_metadata_files(proj, meta_files)
    _write_data_collections_file(proj, meta_files)
    _import_edna_fastdp(proj)


def _makedirs(dir_path):
    os.makedirs(dir_path, mode=0o770, exist_ok=True)


def _create_fragmax_folders(proj):
    """
    create folders that fragmax will use for dataprocessing
    """
    fragmax_dir = path.join(proj.data_path(), "fragmax")

    _makedirs(path.join(fragmax_dir, "logs"))
    _makedirs(path.join(fragmax_dir, "scripts"))
    _makedirs(path.join(fragmax_dir, "models"))
    _makedirs(path.join(fragmax_dir, "export"))
    _makedirs(path.join(fragmax_dir, "results"))
    _makedirs(project_process_protein_dir(proj))


def _write_update_script(proj):
    src_file = path.join(path.dirname(__file__), "data", UPDATE_STATUS_SCRIPT)
    dst_file = project_update_status_script(proj)

    shutil.copy(src_file, dst_file)


def _parse_metafile(proj, metafile):
    def _snapshots():
        for i in range(1, 5):
            snap = node[f"xtalSnapshotFullPath{i}"]
            if snap != "None":
                yield snap

    def _ligand_pic():
        if "Apo" in dataset:
            return "/static/img/apo.png"
        return f"{project_static_url(proj)}/fragmax/process/fragment/{proj.library}/{sample}/{sample}.svg"

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

    return dataset, sample, col_path, run, img_num, resolution,  snaps, _ligand_pic()


def _write_data_collections_file(proj, meta_files):
    dc_file = path.join(project_process_protein_dir(proj), "datacollections.csv")

    with open(dc_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow([
            "imagePrefix", "SampleName", "dataCollectionPath", "Acronym", "dataCollectionNumber",
            "numberOfImages", "resolution", "snapshot", "ligsvg"])

        for mfile in meta_files:
            dataset, sample, col_path, run, img_num, resolution, snaps, ligand = _parse_metafile(proj, mfile)
            writer.writerow([dataset, sample, col_path, proj.protein, run, img_num, resolution, snaps, ligand])


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


def _import_edna_fastdp(proj):
    # Copy data from beamline auto processing to fragmax folders
    # Should be run in a different thread
    h5s = list(itertools.chain(
        *[glob(f"/data/visitors/biomax/{proj.proposal}/{shift}/raw/{proj.protein}/"
               f"{proj.protein}*/{proj.protein}*master.h5")
            for shift in proj.shifts()]))

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
