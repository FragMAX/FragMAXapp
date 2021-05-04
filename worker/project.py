from typing import List
import os
import grp
import stat
import shutil
import celery
from pathlib import Path
from django.conf import settings
from fragview.sites import SITE
from projects.database import db_session
from fragview.crystals import Crystals
from fragview.models import UserProject, Fragment
from fragview.status import scrape_imported_autoproc_status
from fragview.projects import PANDDA_WORKER
from fragview.projects import (
    create_project,
    Project,
    get_dataset_runs,
    get_dataset_metadata,
)


@celery.task
def setup_project(
    project_id: str,
    protein: str,
    proposal: str,
    crystals: List[List[str]],
    import_autoproc: bool,
    encrypted: bool,
):
    try:
        user_proj = UserProject.get(project_id)
        crystals = Crystals.from_list(crystals)

        project = create_project(
            settings.PROJECTS_DB_DIR, project_id, proposal, protein, encrypted
        )

        with db_session:
            _setup_project_folders(project)
            _add_crystals(project, crystals)
            _add_datasets(project)

            if import_autoproc:
                scrape_imported_autoproc_status(project)

        user_proj.set_ready()
    except Exception as e:
        user_proj.set_failed(f"{e}")
        # re-raise exception, so that
        # details are recoded in the worker log
        raise e


def _add_datasets(project: Project):
    for dset_dir in project.get_dataset_dirs():
        _, crystal_id = dset_dir.name.split("-", 1)
        crystal = project.get_crystal(crystal_id)
        if crystal is None:
            # not part of the project
            continue

        for run in get_dataset_runs(dset_dir):
            data_root_dir = dset_dir.parents[2].relative_to(project.proposal_dir)
            meta_data = get_dataset_metadata(project, data_root_dir, crystal_id, run)

            dataset = project.db.DataSet(
                crystal=crystal,
                data_root_dir=str(data_root_dir),
                run=run,
                resolution=meta_data.resolution,
                images=meta_data.num_images,
                start_time=meta_data.start_time,
                end_time=meta_data.end_time,
                wavelength=meta_data.wavelength,
                phi_start=meta_data.axisStart,
                oscillation_range=meta_data.axisRange,
                overlap=meta_data.overlap,
                exposure_time=meta_data.exposureTime,
                detector_distance=meta_data.detectorDistance,
                xbeam=meta_data.xbeam,
                ybeam=meta_data.ybeam,
                beam_shape=meta_data.beamShape,
                transmission=meta_data.transmission,
                slit_gap_horizontal=meta_data.slitGapHorizontal,
                slit_gap_vertical=meta_data.slitGapVertical,
                flux=meta_data.flux,
                beam_size_at_sample_x=meta_data.beamSizeSampleX,
                beam_size_at_sample_y=meta_data.beamSizeSampleY,
            )

            for snapshot_index in meta_data.snapshot_indexes:
                project.db.DataSetSnapshot(dataset=dataset, index=snapshot_index)


def _add_crystals(project: Project, crystals):
    for crystal in crystals:
        fragment = Fragment.get(crystal.FragmentLibrary, crystal.FragmentCode)

        project.db.Crystal(
            id=crystal.SampleID,
            fragment_id=str(fragment.id),
            solvent=crystal.Solvent,
            solvent_concentration=crystal.SolventConcentration,
        )


def _copy_script_files(project: Project, script_files):
    data_dir = Path(Path(__file__).parent, "data")

    for file in script_files:
        src_file = Path(data_dir, file)
        dst_file = Path(project.scripts_dir, file)
        print(f"{src_file} -> {dst_file}")
        shutil.copy(src_file, dst_file)


def _copy_scripts(project):
    script_files = [PANDDA_WORKER]
    if project.encrypted:
        script_files += ["crypt_files.py", "crypt_files.sh"]

    _copy_script_files(project, script_files)


def _setup_project_folders(project: Project):
    #
    # create the project root directory and make sure it:
    #
    #  - it's owner group is set to the proposal group
    #  - the SETGID bit is set
    #
    # this ownership and permission makes all the files created under
    # the project folder accessible to all users in the proposal group

    project_dir = project.project_dir

    # make the root directory
    project_dir.mkdir()

    # look-up proposal group ID
    proposal_group = grp.getgrnam(SITE.get_group_name(project))

    # set owner group
    os.chown(project_dir, -1, proposal_group.gr_gid)

    # make sure SETGID bit is set
    os.chmod(
        project_dir,
        stat.S_IRUSR
        | stat.S_IWUSR
        | stat.S_IXUSR
        | stat.S_ISGID
        | stat.S_IRGRP
        | stat.S_IWGRP
        | stat.S_IXGRP,
    )

    # create misc project subdirectories
    project.logs_dir.mkdir()
    project.system_logs_dir.mkdir()
    project.scripts_dir.mkdir()
    project.process_dir.mkdir()
    project.results_dir.mkdir()
    project.models_dir.mkdir()

    # copy our help scripts to project's directory
    _copy_scripts(project)
