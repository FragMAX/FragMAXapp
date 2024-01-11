from typing import Iterable, Optional
from pathlib import Path
from itertools import count
from django.conf import settings
from fragview import versions
from fragview.sites import plugin
from fragview.sites.plugin import Pipeline, LigandTool, DatasetMetadata
from fragview.sites.maxiv.h5_metadata import read_metadata
from fragview.sites.maxiv.diffractions import get_diffraction_pic_command
from fragview.sites.maxiv.pipelines import PipelineCommands
from fragview.sites.maxiv.beamline import BeamlineInfo
from fragview.sites.maxiv.hpc import HPC


class SitePlugin(plugin.SitePlugin):
    NAME = "MAX IV Laboratory"
    LOGO = "maxiv.png"
    ACCOUNT_STYLE = "DUO"
    AUTH_BACKEND = "fragview.auth.ISPyBBackend"
    RAW_DATA_DIR = "/data/visitors/biomax"
    HPC_JOBS_RUNNER = "slurm"

    def get_project_dir(self, project) -> Path:
        return Path(settings.PROJECTS_ROOT_DIR, f"proj{project.id}")

    def get_project_dataset_dirs(self, project) -> Iterable[Path]:
        for raw_dir in _get_raw_dirs(project):
            for dset_dir in raw_dir.iterdir():
                if dset_dir.name.startswith(project.protein):
                    yield dset_dir

    def get_dataset_runs(self, data_dir: Path) -> Iterable[int]:
        for run_num in count(1):
            master_file = Path(data_dir, f"{data_dir.name}_{run_num}_master.h5")
            if not master_file.is_file():
                break

            yield run_num

    def get_dataset_metadata(
        self, project, dataset_dir: Path, crystal_id: str, run: int
    ) -> Optional[DatasetMetadata]:
        master_file = Path(dataset_dir, f"{crystal_id}_{run}_master.h5")
        return read_metadata(master_file)

    def get_dataset_master_image(self, project, dataset) -> Path:
        return Path(
            project.get_dataset_raw_dir(dataset),
            f"{dataset.name}_master.h5",
        )

    def add_pandda_init_commands(self, batch):
        batch.load_modules(["gopresto", versions.CCP4_MOD, versions.PYMOL_MOD])

    def get_diffraction_picture_command(
        self, project, dataset, angle: int, dest_pic_file
    ) -> list[str]:
        return get_diffraction_pic_command(project, dataset, angle, dest_pic_file)

    def get_beamline_info(self):
        return BeamlineInfo()

    def get_hpc_runner(self):
        return HPC()

    def get_group_name(self, project):
        return f"{project.proposal}-group"

    def dataset_master_image(self, dataset):
        return f"{dataset}_master.h5"

    def get_supported_pipelines(self):
        return {
            Pipeline.AUTO_PROC,
            Pipeline.XIA2_DIALS,
            Pipeline.EDNA_PROC,
            Pipeline.XDSAPP,
            Pipeline.XIA2_XDS,
            Pipeline.DIMPLE,
            Pipeline.FSPIPELINE,
            Pipeline.RHO_FIT,
            Pipeline.LIGAND_FIT,
            Pipeline.PANDDA,
        }

    def get_supported_ligand_tools(self):
        return (
            LigandTool.GRADE,
            {
                LigandTool.GRADE,
                LigandTool.ACEDRG,
                LigandTool.ELBOW,
            },
        )

    def get_pipeline_commands(self):
        return PipelineCommands()

    def get_pandda_inspect_commands(self, pandda_path) -> str:
        return (
            f"module load gopresto CCP4/7.0.072-SHELX-ARP-8.0-0a-PReSTO;"
            f" cd {pandda_path}/pandda; pandda.inspect"
        )


def _get_raw_dirs(project) -> Iterable[Path]:
    for shift_dir in project.proposal_dir.iterdir():
        protein_dir = Path(shift_dir, "raw", project.protein)
        if protein_dir.is_dir():
            yield protein_dir
