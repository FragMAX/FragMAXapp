from typing import Iterable, Tuple, Optional
import conf
from pathlib import Path
from datetime import datetime
from fragview.sites import SITE, current
from fragview.proposals import get_proposals
from fragview.encryption import generate_key
from fragview.sites.plugin import DatasetMetadata
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

    def get_dataset_dirs(self) -> Iterable[Path]:
        return current.get_project_dataset_dirs(self)

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
            f"{dataset.crystal.id}",
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
            f"{dataset.crystal.id}",
            f"{dataset.name}_{dataset_snapshot.index}.snapshot.jpeg",
        )

    #
    # Various project related paths
    #

    @property
    def project_dir(self) -> Path:
        return current.get_project_dir(self)

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
        return current.get_dataset_master_image(self, dataset)

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


def get_dataset_runs(data_dir: Path) -> Iterable[int]:
    return current.get_dataset_runs(data_dir)


def get_dataset_metadata(
    project, dataset_dir: Path, crystal_id: str, run: int
) -> DatasetMetadata:
    return current.get_dataset_metadata(project, dataset_dir, crystal_id, run)


def current_project(request) -> Project:
    proposals = get_proposals(request)
    return request.user.get_current_project(proposals)


def have_pending_projects(request):
    proposals = get_proposals(request)
    return request.user.have_pending_projects(proposals)


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
