import os
import grp
import stat
import shutil
import pandas
from pathlib import Path
from django.core.management.base import BaseCommand
from fragview.status import scrape_imported_autoproc_status
from fragview.models import UserProject, Library, Fragment
from fragview.projects import (
    Project,
    create_project,
    get_dataset_runs,
    get_dataset_metadata,
)
from fragview.sites import SITE
from projects.database import db_session
from fragview.projects import PANDDA_WORKER


def _load_proj_csv(csv_file: Path):
    return pandas.read_csv(csv_file)


def _get_project_entry(proposal) -> UserProject:
    proj = UserProject(proposal=proposal)
    proj.save()

    return proj


def _parse_concentration(concentration):
    concentration = concentration.strip()
    if not concentration.endswith("%"):
        raise Exception("parse error")

    return float(concentration[:-1]) / 100.0


def _add_crystals(project: Project, crystals):
    for _, row in crystals.iterrows():
        # TODO: handle cases when specified library or fragment not found
        # TODO: we will get (Library|Fragment).DoesNotExist exception
        fragment = Fragment.get(row.FragmentLibrary, row.FragmentCode)

        project.db.Crystal(
            id=row.SampleID,
            fragment_id=str(fragment.id),
            solvent=row.Solvent,
            solvent_concentration=_parse_concentration(row.SolventConcentration),
        )


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


class Command(BaseCommand):
    help = "create project from CSV file, temporary for development"

    def add_arguments(self, parser):
        parser.add_argument("proposal", type=str)
        parser.add_argument("project_csv", type=str)

    def handle(self, *args, **options):
        proj_csv = Path(options["project_csv"])
        proposal = options["proposal"]
        proj_entry = _get_project_entry(proposal)

        project = create_project(proj_entry.id, proposal, proj_csv.stem)
        proj_entry.set_pending()

        with db_session:
            _setup_project_folders(project)
            _add_crystals(project, _load_proj_csv(proj_csv))
            _add_datasets(project)

            scrape_imported_autoproc_status(project)

        proj_entry.set_ready()
