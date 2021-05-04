from typing import Iterator, Tuple, Optional
import glob
import conf
from os import path
from pathlib import Path
from datetime import datetime
from itertools import count
from django.conf import settings
from fragview.sites import SITE
from fragview.proposals import get_proposals
from fragview.xsdata import XSDataCollection
from fragview.encryption import generate_key
from projects.database import (
    create_project_db,
    get_project_db,
    desc,
)

# make this exception available for import as 'fragview.projects.ProjectNotFound'
from projects.database import ProjectNotFound  # noqa F401

PANDDA_WORKER = "pandda_prepare_runs.py"


class Project:
    """
    main entry point to access data related to a specific project

    provides an API over both database and file system stored project
    data
    """

    # number of unique project icons available
    PROJ_ICONS_NUMBER = 10

    def __init__(self, project_db, proj_id):
        self.db = project_db
        self.id = proj_id
        self._project_model_obj = None

    #
    # Database access
    #

    @property
    def _project_model(self):
        if self._project_model_obj is None:
            self._project_model_obj = self.db.Project.select().first()
        return self._project_model_obj

    @property
    def protein(self) -> str:
        return self._project_model.protein

    @property
    def proposal(self) -> str:
        return self._project_model.proposal

    @property
    def encrypted(self) -> bool:
        return self._project_model.encrypted

    @property
    def encryption_key(self):
        return self._project_model.encryption_key

    @encryption_key.setter
    def encryption_key(self, key):
        self._project_model.encryption_key = key

    def has_encryption_key(self) -> bool:
        return self.encryption_key is not None

    def forget_key(self):
        self._project_model.encryption_key = None

    def get_crystal(self, crystal_id: str):
        return self.db.Crystal.get(id=crystal_id)

    def get_crystals(self):
        return self.db.Crystal.select()

    def get_datasets(self):
        return self.db.DataSet.select()

    def get_dataset(self, dataset_id):
        """
        get DataSet by ID
        """
        return self.db.DataSet.get(id=dataset_id)

    def get_pdbs(self):
        return self.db.PDB.select()

    def get_pdb(self, pdb_id):
        return self.db.PDB.get(id=pdb_id)

    def get_refine_results(self):
        return self.db.RefineResult.select()

    def get_refine_result(self, refine_result_id):
        return self.db.RefineResult.get(id=refine_result_id)

    def get_ligfit_result(self, ligfit_result_id):
        return self.db.LigfitResult.get(id=ligfit_result_id)

    def get_datasets_process_results(self, dataset):
        return self.db.ProcessResult.select(lambda r: r.result.dataset == dataset)

    def get_datasets_refine_results(self, dataset):
        return self.db.RefineResult.select(lambda r: r.result.dataset == dataset)

    def get_dataset_snapshot(self, dataset_id, index):
        dataset = self.get_dataset(dataset_id)
        if dataset is None:
            return

        return self.db.DataSetSnapshot.get(dataset=dataset, index=index)

    def get_data_collection_dates(self) -> Optional[Tuple[datetime, datetime]]:
        """
        get datetime(s) for when earliest and latest dataset was recorded

        returns None if the project does not have any datasets
        """
        earliest = self.get_datasets().order_by(self.db.DataSet.start_time)
        latest = self.get_datasets().order_by(desc(self.db.DataSet.end_time))

        if not earliest.exists():
            # project does not have any datasets
            return None

        return earliest.first().start_time, latest.first().end_time

    #
    # File system access
    #

    def _get_raw_dirs(self):
        for sdir in self.proposal_dir.iterdir():
            protein_dir = Path(sdir, "raw", self.protein)
            if protein_dir.is_dir():
                yield protein_dir

    def get_dataset_dirs(self) -> Iterator[Path]:
        for raw_dir in self._get_raw_dirs():
            for dset_dir in raw_dir.iterdir():
                if dset_dir.name.startswith(self.protein):
                    yield dset_dir

    @property
    def proposal_dir(self) -> Path:
        return Path(SITE.RAW_DATA_DIR, self.proposal)

    def get_dataset_root_dir(self, dataset) -> Path:
        return Path(self.proposal_dir, dataset.data_root_dir)

    def get_dataset_raw_dir(self, dataset) -> Path:
        return Path(
            self.get_dataset_root_dir(dataset),
            "raw",
            self.protein,
            f"{self.protein}-{dataset.crystal.id}",
        )

    def get_dataset_snapshot_path(self, dataset_snapshot) -> Path:
        """
        path to the dataset snapshot's file
        """
        dataset = dataset_snapshot.dataset
        return Path(
            conf.SNAPSHOTS_ROOT_DIR,
            self.proposal,
            dataset.data_root_dir,
            "raw",
            self.protein,
            f"{self.protein}-{dataset.crystal.id}",
            f"{self.protein}-{dataset.name}_{dataset_snapshot.index}.snapshot.jpeg",
        )

    #
    # Various project related paths
    #

    @property
    def project_dir(self) -> Path:
        return Path(settings.PROJECTS_ROOT_DIR, f"proj{self.id}")

    @property
    def process_dir(self) -> Path:
        return Path(self.project_dir, "process")

    @property
    def results_dir(self) -> Path:
        return Path(self.project_dir, "results")

    @property
    def pandda_dir(self) -> Path:
        return Path(self.project_dir, "pandda")

    @property
    def models_dir(self) -> Path:
        return Path(self.project_dir, "models")

    @property
    def scripts_dir(self) -> Path:
        return Path(self.project_dir, "scripts")

    @property
    def logs_dir(self) -> Path:
        return Path(self.project_dir, "logs")

    @property
    def system_logs_dir(self) -> Path:
        return Path(self.logs_dir, "system")

    def pandda_method_dir(self, method: str) -> Path:
        return Path(self.pandda_dir, method)

    def pandda_processed_datasets_dir(self, method: str) -> Path:
        """
        path to PanDDa 'processed datasets' directory for specified method
        """
        return Path(
            self.pandda_method_dir(method),
            "pandda",
            "processed_datasets",
        )

    def pandda_processed_dataset_dir(self, method: str, dataset_name: str) -> Path:
        """
        path to PanDDa 'processed datasets' directory for
        specified method and dataset
        """
        return Path(
            self.pandda_processed_datasets_dir(method),
            dataset_name,
        )

    def get_log_path(self, log_file) -> Path:
        return Path(self.logs_dir, log_file)

    def get_dataset_process_dir(self, dataset) -> Path:
        return Path(self.process_dir, f"{dataset.name}")

    def get_dataset_results_dir(self, dataset) -> Path:
        return Path(self.results_dir, f"{dataset.name}")

    def get_dataset_master_image(self, dataset) -> Path:
        # TODO: must be deployment-site specific
        return Path(
            self.get_dataset_raw_dir(dataset),
            f"{self.protein}-{dataset.name}_master.h5",
        )

    def get_refine_result_dir(self, refine_result) -> Path:
        processed_data = refine_result.result

        return Path(
            self.get_dataset_results_dir(refine_result.dataset),
            processed_data.input.tool,
            processed_data.tool,
        )

    def get_pdb_file(self, pdb) -> Path:
        """
        absolute path to user uploaded PDB file
        """
        return Path(self.models_dir, pdb.filename)

    #
    # User presentation support
    #
    @property
    def name(self):
        """
        user visible name of the project
        """
        return f"{self.protein} ({self.proposal})"

    def icon_num(self):
        return self.id % self.PROJ_ICONS_NUMBER


def create_project(
    projects_db_dir: Path,
    project_id: str,
    proposal: str,
    protein: str,
    encrypted: bool,
) -> Project:
    # generation encryption key, for encrypted projects
    encryption_key = generate_key() if encrypted else None
    proj_db = create_project_db(
        projects_db_dir, project_id, proposal, protein, encryption_key
    )

    return Project(proj_db, project_id)


def get_project(projects_db_dir: Path, project_id: str) -> Project:
    return Project(get_project_db(projects_db_dir, project_id), project_id)


def get_dataset_runs(data_dir: Path) -> Iterator[int]:
    for run_num in count(1):
        master_file = Path(data_dir, f"{data_dir.name}_{run_num}_master.h5")
        if not master_file.is_file():
            break

        yield run_num


def get_dataset_metadata(
    project: Project, data_root_dir: Path, crystal_id: str, run: int
) -> XSDataCollection:
    # TODO: we should probably have some site independant class for meta data, instead of XSDataCollection
    # TODO: like DataSetMeta, where each site would provide it's own implementation
    protein = project.protein
    fastdp_dir = Path(
        project.proposal_dir,
        data_root_dir,
        "process",
        protein,
        f"{protein}-{crystal_id}",
        f"xds_{protein}-{crystal_id}_{run}_1",
        "fastdp",
    )

    xml_file = next(
        fastdp_dir.glob(
            str(
                Path(
                    "cn*",
                    "ISPyBRetrieveDataCollectionv1_4",
                    "ISPyBRetrieveDataCollectionv1_4_dataOutput.xml",
                )
            )
        ),
        None,
    )

    if xml_file is None:
        # TODO: think about exceptions
        raise Exception(f"no XML file found for {crystal_id} {run}")

    return XSDataCollection(xml_file)


def current_project(request) -> Project:
    proposals = get_proposals(request)
    return request.user.get_current_project(proposals)


def have_pending_projects(request):
    proposals = get_proposals(request)
    return request.user.have_pending_projects(proposals)


def proposal_dir(proposal_number):
    return path.join(SITE.RAW_DATA_DIR, proposal_number)


def shift_dir(proposal_number, shift):
    return path.join(proposal_dir(proposal_number), shift)


# TODO remove me?
def parse_dataset_name(dset_name):
    """
    split full dataset name into sample name and run number

    e.g. 'Nsp10-apo33_1' becomes 'Nsp10-apo33' and 1
    """
    return dset_name.rsplit("_", 1)


# TODO remove me?
def dataset_xml_file(project, data_set):
    set_name, _ = parse_dataset_name(data_set)

    return Path(project_process_protein_dir(project), set_name, f"{data_set}.xml")


# TODO remove me?
def dataset_master_image(dataset):
    return SITE.dataset_master_image(dataset)


def protein_dir(proposal_number, shift, protein):
    return path.join(shift_dir(proposal_number, shift), "raw", protein)


def project_raw_protein_dir(project):
    return protein_dir(project.proposal, project.shift, project.protein)


def project_shift_dirs(project):
    for shift in project.shifts():
        yield shift_dir(project.proposal, shift)


# TODO: remove me
def project_fragmax_dir(project):
    return path.join(project.data_path(), "fragmax")


def project_process_dir(project):
    return path.join(project_fragmax_dir(project), "process")


def project_fragments_dir(project):
    return path.join(project_fragmax_dir(project), "fragments")


def project_results_dir(project):
    return path.join(project_fragmax_dir(project), "results")


def project_results_dataset_dir(project, dataset) -> Path:
    return Path(project_results_dir(project), dataset)


def project_models_dir(project):
    return path.join(project_fragmax_dir(project), "models")


# TODO: remove me ?
def project_scripts_dir(project):
    return path.join(project.data_path(), "fragmax", "scripts")


# TODO: remove me ?
def project_logs_dir(project):
    return path.join(project_fragmax_dir(project), "logs")


def project_pandda_results_dir(project):
    return path.join(project_fragmax_dir(project), "results", "pandda", project.protein)


def project_pandda_processed_dataset_dir(project, method, dataset):
    return Path(
        project_pandda_results_dir(project),
        method,
        "pandda",
        "processed_datasets",
        dataset,
    )


def project_model_file(project, model_file):
    return path.join(project_models_dir(project), model_file)


def project_process_protein_dir(project):
    return path.join(project_process_dir(project), project.protein)


def project_process_dataset_dir(project, dataset) -> Path:
    sample, _ = parse_dataset_name(dataset)
    return Path(project_process_protein_dir(project), sample, dataset)


def project_process_tool_dir(project, dataset, tool) -> Path:
    return Path(project_process_dataset_dir(project, dataset), tool)


def project_results_file(project):
    return path.join(project_process_protein_dir(project), "results.csv")


def project_all_status_file(project):
    return path.join(project_process_protein_dir(project), "allstatus.csv")


def project_data_collections_file(project):
    return path.join(project_process_protein_dir(project), "datacollections.csv")


def project_script(project: Project, script_file) -> str:
    """
    generate full path to a file named 'script_file' inside project's script directory
    """
    return str(Path(project.scripts_dir, script_file))


def project_log_path(project: Project, log_file) -> str:
    """
    generate full path to a file name 'log_file' inside project's logs directory
    """
    return str(Path(project.logs_dir, log_file))


def project_syslog_path(project: Project, log_file) -> str:
    return str(Path(project.system_logs_dir, log_file))


def shifts_raw_master_h5_files(project, shifts):
    """
    generate a list of .h5 image files from the 'raw' directory
    for specified shits

    shifts - list of shift
    """
    shift_dirs = [shift_dir(project.proposal, s) for s in shifts]
    for sdir in shift_dirs:
        for file in glob.glob(f"{sdir}/raw/{project.protein}/*/*master.h5"):
            yield file


def project_raw_master_h5_files(project):
    return shifts_raw_master_h5_files(project, project.shifts())


def project_datasets(project):
    return SITE.get_project_datasets(project)


def shifts_xml_files(project, shifts):
    """
    generate a list of metadata collection xml files for
    the specified project's shifts

    shifts - list of shift
    """
    shift_dirs = [shift_dir(project.proposal, s) for s in shifts]
    for sdir in shift_dirs:
        for file in glob.glob(
            f"{sdir}**/process/{project.protein}/**/**/fastdp/cn**/"
            f"ISPyBRetrieveDataCollectionv1_4/ISPyBRetrieveDataCollectionv1_4_dataOutput.xml"
        ):
            yield file


def project_xml_files(project):
    return shifts_xml_files(project, project.shifts())


def project_fragment_cif(project, fragment):
    return path.join(project_fragments_dir(project), f"{fragment}.cif")


def project_fragment_pdb(project, fragment):
    return path.join(project_fragments_dir(project), f"{fragment}.pdb")


def project_model_path(project, pdb_file):
    return path.join(project.data_path(), "fragmax", "models", pdb_file)


def project_static_url(project):
    return path.join("/", "static", "biomax", project.proposal, project.shift)
