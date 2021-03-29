import os
from os import path
import grp
import csv
import stat
from glob import glob
import shutil
import celery
from celery.utils.log import get_task_logger
from fragview import dist_lock
from worker.xsdata import copy_collection_metadata_files
from fragview.sites import SITE
from fragview.fileio import makedirs
from fragview.models import Project
from fragview.xsdata import XSDataCollection
from fragview.status import set_imported_autoproc_status
from fragview.projects import project_xml_files, project_process_protein_dir
from fragview.projects import project_data_collections_file, project_fragmax_dir
from fragview.projects import project_shift_dirs, project_all_status_file, project_fragments_dir
from fragview.projects import UPDATE_STATUS_SCRIPT, PANDDA_WORKER, UPDATE_RESULTS_SCRIPT
from fragview.projects import shifts_xml_files, project_scripts_dir

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
    copy_collection_metadata_files(proj, meta_files)
    _write_data_collections_file(proj, project_xml_files(proj))
    _write_project_status(proj)


def _setup_project_files(proj):
    _create_fragmax_folders(proj)
    meta_files = SITE.create_meta_files(proj)
    _copy_scripts(proj)
    _write_data_collections_file(proj, meta_files)
    SITE.prepare_project_folders(proj, proj.shifts())
    _write_project_status(proj)


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
    proposal_group = grp.getgrnam(SITE.get_group_name(proj))

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

    makedirs(path.join(fragmax_dir, "logs", "system"))
    makedirs(path.join(fragmax_dir, "scripts"))
    makedirs(path.join(fragmax_dir, "models"))
    makedirs(path.join(fragmax_dir, "export"))
    makedirs(path.join(fragmax_dir, "results"))
    makedirs(project_fragments_dir(proj))
    makedirs(project_process_protein_dir(proj))


def _copy_script_files(proj, script_files):
    data_dir = path.join(path.dirname(__file__), "data")
    dest_dir = project_scripts_dir(proj)

    for file in script_files:
        src_file = path.join(data_dir, file)
        dst_file = path.join(dest_dir, file)
        print(f"{src_file} -> {dst_file}")
        shutil.copy(src_file, dst_file)


def _copy_scripts(proj):
    script_files = [UPDATE_STATUS_SCRIPT, PANDDA_WORKER, UPDATE_RESULTS_SCRIPT]
    if proj.encrypted:
        script_files += ["crypt_files.py", "crypt_files.sh"]

    _copy_script_files(proj, script_files)


def _parse_metafile(metafile):
    xsdata = XSDataCollection(metafile)

    sample = xsdata.imagePrefix.split("-")[-1]
    resolution = f"{xsdata.resolution:.2f}"

    snapshots = xsdata.snapshots
    snapshots = ",".join(snapshots) \
        if len(snapshots) > 0 \
        else "noSnapshots"  # TODO drop this, use empty string as 'no snapshots' value

    return xsdata.imagePrefix, sample, xsdata.imageDirectory, xsdata.dataCollectionNumber, \
        xsdata.numberOfImages, resolution, snapshots


def _write_data_collections_file(proj, meta_files):
    dc_file = project_data_collections_file(proj)
    logger.info(f"writing {dc_file}")

    with open(dc_file, "w") as f:
        writer = csv.writer(f)
        writer.writerow([
            "imagePrefix", "SampleName", "dataCollectionPath", "Acronym", "dataCollectionNumber",
            "numberOfImages", "resolution", "snapshot"])

        for mfile in meta_files:
            dataset, sample, col_path, run, img_num, resolution, snaps = _parse_metafile(mfile)
            writer.writerow([dataset, sample, col_path, proj.protein, run, img_num, resolution, snaps])


def _write_project_status(proj):
    logger.info("writing project status")

    statusDict = dict()
    procList = list()

    for shift_dir in project_shift_dirs(proj):
        procList += [
            "/".join(x.split("/")[:8]) + "/" + x.split("/")[-2] + "/" for x in
            glob(f"{shift_dir}/fragmax/process/{proj.protein}/*/*/")]

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

    with open(project_all_status_file(proj), "w") as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(["dataset_run", "autoproc", "dials", "EDNA", "fastdp", "xdsapp",
                         "xdsxscale", "dimple", "fspipeline", "buster", "ligfit", "rhofit"])
        for dataset_run, status in statusDict.items():
            writer.writerow([dataset_run] + list(status.values()))

    set_imported_autoproc_status(proj)
