from typing import Iterable, Optional
from pathlib import Path
from django.conf import settings
from fragview.sites import plugin
from fragview.sites.plugin import Pipeline, LigandTool, DatasetMetadata
from fragview.sites.hzb.cbf import parse_metadata
from fragview.sites.hzb.utils import get_dataset_frame_image
from fragview.sites.hzb.diffractions import get_diffraction_pic_command
from fragview.sites.hzb.pipelines import PipelineCommands
from fragview.sites.hzb.beamline import BeamlineInfo
from fragview.sites.hzb.hpc import HPC

# filename suffix for a dataset's master image file
MASTER_IMG_SUFFIX = "_0001.cbf"

# max number of dataset runs we'll look for
MAX_RUNS = 8


class SitePlugin(plugin.SitePlugin):
    NAME = "Helmholtz-Zentrum Berlin"
    LOGO = "hzb.png"
    DISABLED_FEATURES = ["proposals", "autoproc_import"]
    AUTH_BACKEND = "fragview.auth.LocalBackend"
    RAW_DATA_DIR = "/data/fragmaxrpc/user"
    HPC_JOBS_RUNNER = "local"

    def get_project_dir(self, project) -> Path:
        return Path(
            settings.PROJECTS_ROOT_DIR, project.proposal, "fragmax", f"proj{project.id}"
        )

    def get_project_dataset_dirs(self, project) -> Iterable[Path]:
        protein_dir = Path(
            settings.PROJECTS_ROOT_DIR, project.proposal, "raw", project.protein
        )
        return protein_dir.iterdir()

    def get_dataset_runs(self, data_dir: Path) -> Iterable[int]:
        prefix = f"{data_dir.name}_"
        postfix = "_0001.cbf"
        for master_file in data_dir.glob(f"{prefix}*{postfix}"):
            run_num = master_file.name[len(prefix) : -len(postfix)]
            yield int(run_num)

    def get_dataset_metadata(
        self, project, dataset_dir: Path, crystal_id: str, run: int
    ) -> Optional[DatasetMetadata]:
        cbf_file = Path(dataset_dir, f"{crystal_id}_{run}_0001.cbf")
        return parse_metadata(cbf_file)

    def get_dataset_master_image(self, project, dataset) -> Path:
        return get_dataset_frame_image(project, dataset, 1)

    def get_diffraction_picture_command(
        self, project, dataset, angle: int, dest_pic_file
    ) -> list[str]:
        return get_diffraction_pic_command(project, dataset, angle, dest_pic_file)

    def get_beamline_info(self):
        return BeamlineInfo()

    def get_hpc_runner(self):
        return HPC()

    def get_group_name(self, project):
        return project.proposal

    def dataset_master_image(self, dataset):
        return f"{dataset}{MASTER_IMG_SUFFIX}"

    def get_supported_pipelines(self):
        return {
            Pipeline.XIA2_DIALS,
            Pipeline.XDSAPP,
            Pipeline.XIA2_XDS,
            Pipeline.DIMPLE,
            Pipeline.FSPIPELINE,
            Pipeline.LIGAND_FIT,
            Pipeline.PANDDA,
        }

    def get_supported_ligand_tools(self):
        return LigandTool.ACEDRG, {LigandTool.ACEDRG, LigandTool.ELBOW}

    def get_pipeline_commands(self):
        return PipelineCommands()
