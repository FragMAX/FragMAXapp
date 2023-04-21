from typing import Optional
import os
import grp
import stat
import shutil
import celery
from pathlib import Path
from fragview.sites import SITE
from projects.database import db_session
from fragview.crystals import Crystals, Crystal
from fragview.fraglibs import create_db_library, LibraryType
from fragview.models import UserProject, Fragment
from fragview.status import scrape_imported_autoproc_status
from fragview.projects import PANDDA_WORKER
from fragview.projects import (
    create_project,
    get_project,
    Project,
    get_dataset_runs,
    get_dataset_metadata,
)


@celery.shared_task
def setup_project(
    project_id: str,
    protein: str,
    proposal: str,
    crystals: list[dict[str, str]],
    libraries: dict[str, LibraryType],
    import_autoproc: bool,
):
    try:
        print(f"setting up project, ID {project_id}: {protein} ({proposal})")
        user_proj = UserProject.get(project_id)

        project = create_project(project_id, proposal, protein)

        with db_session:
            _create_frag_libs(project, libraries)
            _setup_project_folders(project)
            _add_crystals(project, Crystals.from_list(crystals))
            _add_datasets(project)

            if import_autoproc:
                scrape_imported_autoproc_status(project)

        user_proj.set_ready()
    except Exception as e:
        user_proj.set_failed(f"{e}")
        # re-raise exception, so that
        # details are recoded in the worker log
        raise e


@celery.shared_task
def import_crystals(project_id: str, crystals: list[dict[str, str]]):
    try:
        print(f"importing crystals to project ID: {project_id}")

        with db_session:
            project = get_project(project_id)
            _add_crystals(project, Crystals.from_list(crystals))
            _add_datasets(project)

    except Exception as e:
        UserProject.get(project_id).set_failed(f"{e}")
        # re-raise exception, so that
        # details are recoded in the worker log
        raise e

    UserProject.get(project_id).set_ready()


def _add_datasets(project: Project):
    """
    For all the project's crystals, look for datasets on the file system.
    Add database entries for all new datasets found on the file system.
    """

    def dataset_exists(crystal, run: int):
        dset = crystal.get_dataset(run)
        return dset is not None

    for dset_dir in project.get_dataset_dirs():
        crystal_id = dset_dir.name
        crystal = project.get_crystal(crystal_id)
        if crystal is None:
            # not part of the project
            continue

        for run in get_dataset_runs(dset_dir):
            if dataset_exists(crystal, run):
                # skip already existing dataset
                continue

            meta_data = get_dataset_metadata(project, dset_dir, crystal_id, run)
            if meta_data is None:
                print(
                    f"warning: no meta-data found for {crystal_id} {run}, skipping the dataset"
                )
                continue

            # TODO: this is MAXIV specific, think about site-independent style
            shift_dir = dset_dir.parents[2].relative_to(project.proposal_dir)

            dataset = project.db.DataSet(
                crystal=crystal,
                data_root_dir=str(shift_dir),
                run=run,
                detector=meta_data.detector,
                resolution=meta_data.resolution,
                images=meta_data.images,
                start_time=meta_data.start_time,
                end_time=meta_data.end_time,
                wavelength=meta_data.wavelength,
                start_angle=meta_data.start_angle,
                angle_increment=meta_data.angle_increment,
                exposure_time=meta_data.exposure_time,
                detector_distance=meta_data.detector_distance,
                xbeam=meta_data.xbeam,
                ybeam=meta_data.ybeam,
                beam_shape=meta_data.beam_shape,
                transmission=meta_data.transmission,
                slit_gap_horizontal=meta_data.slit_gap_horizontal,
                slit_gap_vertical=meta_data.slit_gap_vertical,
                flux=meta_data.flux,
                beam_size_at_sample_x=meta_data.beam_size_at_sample_x,
                beam_size_at_sample_y=meta_data.beam_size_at_sample_y,
            )

            for snapshot_index in meta_data.snapshot_indices:
                project.db.DataSetSnapshot(dataset=dataset, index=snapshot_index)


def _add_crystals(project: Project, crystals: Crystals):
    """
    Add provided crystals to project's database.

    Note: any crystals already defined in the database will be ignored.
    """

    def get_fragment_id(crystal: Crystal) -> Optional[str]:
        fragment = crystal.get_fragment()
        if fragment is None:
            # pony ORM uses empty string as 'None'
            return ""

        db_frag = Fragment.get(project, fragment.library, fragment.code)
        return str(db_frag.id)

    def crystal_exist(crystal_id: str):
        crystal = project.get_crystal(crystal_id)
        return crystal is not None

    for crystal in crystals:
        if crystal_exist(crystal.SampleID):
            # skip already existing Crystal
            continue

        project.db.Crystal(
            id=crystal.SampleID,
            fragment_id=get_fragment_id(crystal),
        )


def _copy_script_files(project: Project, script_files):
    data_dir = Path(Path(__file__).parent, "data")

    for file in script_files:
        src_file = Path(data_dir, file)
        dst_file = Path(project.scripts_dir, file)
        print(f"{src_file} -> {dst_file}")
        shutil.copy(src_file, dst_file)


def _copy_scripts(project):
    _copy_script_files(project, [PANDDA_WORKER])


def _create_frag_libs(project: Project, libraries: dict[str, dict[str, str]]):
    for name, fragments in libraries.items():
        create_db_library(project, name, fragments)


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
    project_dir.mkdir(parents=True)

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
