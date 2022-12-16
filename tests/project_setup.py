from pathlib import Path
from collections import namedtuple
from datetime import datetime
from fragview import models
from fragview.projects import create_project
from fragview.scraper import PROC_TOOLS, REFINE_TOOLS
from projects.database import db_session

DUMMY_START_TIME = datetime(2019, 10, 22, 12, 30)
DUMMY_END_TIME = datetime(2019, 10, 22, 12, 31)

Project = namedtuple(
    "Project", ["protein", "proposal", "crystals", "datasets", "results"]
)
Crystal = namedtuple("Crystal", ["sample_id", "library_name", "fragment_code"])
DataSet = namedtuple("DataSet", ["crystal_id", "run"])
Result = namedtuple("Result", ["dataset", "tool", "input_tool", "result"])


def _populate_fragments_db(project_desc: Project):
    """
    for all of project's crystals, create Library and Fragment entries
    """

    def _create_library(library_name: str) -> models.Library:
        """
        if no Library entry with specified name exists, create and return it
        """
        lib = models.Library.objects.filter(name=library_name).first()
        if lib is None:
            lib = models.Library(name=library_name)
            lib.save()

        return lib

    def _create_fragment(library: models.Library, code: str):
        """
        if no Fragment with specified library and code exist, create it
        """
        frag = models.Fragment.objects.filter(
            library=library,
            code=code,
        ).first()

        if frag is None:
            # use dummy SMILES
            models.Fragment(library=library, code=code, smiles="CNCC1=NC=CS1").save()

    for crystal in project_desc.crystals:
        if crystal.library_name is None and crystal.fragment_code is None:
            # Apo crystal, skip it
            continue

        library = _create_library(crystal.library_name)
        _create_fragment(library, crystal.fragment_code)


@db_session
def populate_project_db(project, project_desc: Project):
    def find_result(dataset, tool: str):
        # work-around for finding 'Result' with specified
        # 'DataSet' and tool name,
        # as normal db.Result.get() queries does not
        # always work, for some reason
        for res in dataset.result:
            if res.tool == tool:
                return res

    def get_fragment_id(library_name: str, fragment_code: str) -> str:
        if library_name is None and fragment_code is None:
            # Apo crystal, return 'orm' version of 'None' fragment
            return ""

        frag = models.Fragment.get(project, library_name, fragment_code)
        return str(frag.id)

    #
    # create 'crystals' entries
    #
    for crystal in project_desc.crystals:
        project.db.Crystal(
            id=crystal.sample_id,
            fragment_id=get_fragment_id(crystal.library_name, crystal.fragment_code),
        )

    #
    # create 'datasets' entries
    #
    for dataset in project_desc.datasets:
        crystal = project.get_crystal(dataset.crystal_id)

        project.db.DataSet(
            crystal=crystal,
            run=dataset.run,
            # some hardcoded dummy values for now
            data_root_dir="20211125",
            detector="EIGER 16M",
            resolution=1.2,
            images=1800,
            start_time=DUMMY_START_TIME,
            end_time=DUMMY_END_TIME,
            wavelength=0.92,
            start_angle=43.0,
            angle_increment=0.1,
            exposure_time=39.2,
            detector_distance=152.44,
            xbeam=2100.77,
            ybeam=2120.31,
            beam_shape="ellipse",
            transmission=0.12,
            slit_gap_horizontal=50.0,
            slit_gap_vertical=50.0,
            flux=263000000000.0,
            beam_size_at_sample_x=50.0,
            beam_size_at_sample_y=50.0,
        )

    #
    # create 'results' entries
    #
    for result_desc in project_desc.results:
        crystal_id, run = result_desc.dataset
        crystal = project.get_crystal(crystal_id)
        dataset = project.db.DataSet.get(crystal=crystal, run=run)

        result = project.db.Result(
            dataset=dataset, tool=result_desc.tool, result=result_desc.result
        )

        # if result of process tool add 'process result' entry
        if result_desc.tool in PROC_TOOLS:
            project.db.ProcessResult(
                result=result,
                # some hardcoded dummy values for now
                space_group="C 2 2 2",
                unit_cell_a=43.783,
                unit_cell_b=85.432,
                unit_cell_c=161.728,
                unit_cell_alpha=90.0,
                unit_cell_beta=90.0,
                unit_cell_gamma=90.0,
                low_resolution_average=41.3,
                high_resolution_average=1.49,
                low_resolution_out=1.54,
                high_resolution_out=1.49,
                reflections=240997,
                unique_reflections=46616,
                multiplicity=5.2,
                i_sig_average=2.7,
                i_sig_out=-0.1,
                r_meas_average=0.53,
                r_meas_out=-66.413,
                completeness_average=78.1,
                completeness_out=35.9,
            )

        # if result of refine tool add 'refine result' entry
        if result_desc.tool in REFINE_TOOLS:
            project.db.RefineResult(
                result=result,
                # some hardcoded dummy values for now
                space_group="P1211",
                resolution=1.06,
                r_work=0.17461,
                r_free=0.18823,
                rms_bonds=0.015,
                rms_angles=1.914,
                unit_cell_a=42.38,
                unit_cell_b=41.39,
                unit_cell_c=72.38,
                unit_cell_alpha=90.0,
                unit_cell_beta=104.29,
                unit_cell_gamma=90.0,
                blobs="[]",
            )

            input_result = find_result(dataset, result_desc.input_tool)
            result.input = input_result


def create_temp_project(projects_db_dir: Path, project_desc: Project):
    # create UserProject entry in the django database
    user_proj = models.UserProject(proposal=project_desc.proposal)
    user_proj.save()

    # create the project database file
    projects_db_dir.mkdir(parents=True, exist_ok=True)
    project = create_project(
        user_proj.id,
        project_desc.proposal,
        project_desc.protein,
    )

    _populate_fragments_db(project_desc)

    # add entries from project description to the database
    populate_project_db(project, project_desc)

    return project
