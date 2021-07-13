from typing import List, Iterable
from os import path, walk
from pathlib import Path
from datetime import datetime
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
    DISABLED_FEATURES = ["soaking_plan", "proposals", "autoproc_import"]
    AUTH_BACKEND = "fragview.auth.LocalBackend"
    RAW_DATA_DIR = "/data/fragmaxrpc/user"
    HPC_JOBS_RUNNER = "local"

    def get_project_dir(self, project) -> Path:
        return Path(settings.PROJECTS_ROOT_DIR, project.proposal, "fragmax")

    def get_project_dataset_dirs(self, project) -> Iterable[Path]:
        protein_dir = Path(self.get_project_dir(project).parent, "raw", project.protein)
        return protein_dir.iterdir()

    def get_dataset_runs(self, data_dir: Path) -> Iterable[int]:
        prefix = f"{data_dir.name}_"
        postfix = "_0001.cbf"
        for master_file in data_dir.glob(f"{prefix}*{postfix}"):
            run_num = master_file.name[len(prefix) : -len(postfix)]
            yield int(run_num)

    def get_dataset_metadata(
        self, project, dataset_dir: Path, crystal_id: str, run: int
    ) -> DatasetMetadata:
        cbf_file = Path(dataset_dir, f"{project.protein}-{crystal_id}_{run}_0001.cbf")
        return parse_metadata(cbf_file)

    def get_dataset_master_image(self, project, dataset) -> Path:
        return get_dataset_frame_image(project, dataset, 1)

    def add_pandda_init_commands(self, batch):
        batch.add_command(
            "source /soft/pxsoft/64/ccp4/ccp4-6.5.0/ccp4-7.0/bin/ccp4.setup-csh"
        )

    def get_project_experiment_date(self, project):
        return _get_experiment_timestamp(project)

    def get_diffraction_picture_command(
        self, project, dataset, angle: int, dest_pic_file
    ) -> List[str]:
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
        # disable AceDRG until issue #11 is resolved
        # return LigandTool.ACEDRG, {LigandTool.ACEDRG, LigandTool.ELBOW}
        return LigandTool.ELBOW, {LigandTool.ELBOW}

    def get_pipeline_commands(self):
        return PipelineCommands()

    def get_pandda_inspect_commands(self, pandda_path) -> str:
        #
        # generate a pandda path relative to the user's home directory
        #
        # we can't use pandda_path as-is for launching pandda.inspect,
        # as fragmax directory is mounted differently on other computers
        #
        pandda_path = Path(pandda_path)
        parent = pandda_path.parents[len(pandda_path.parents) - 5]
        cd_path = Path("~", pandda_path.relative_to(parent), "pandda")

        return (
            f"source /soft/pxsoft/64/ccp4/ccp4-6.5.0/ccp4-7.0/bin/ccp4.setup-csh; "
            f"cd {cd_path}; pandda.inspect"
        )


def _get_experiment_timestamp(project):
    def _find_path():
        from fragview.projects import project_raw_protein_dir

        raw = project_raw_protein_dir(project)

        # look for any random CBF folder inside raw folder
        for dir_name, _, files in walk(raw):
            for fname in files:
                _, ext = path.splitext(fname)
                if ext.lower() == ".cbf":
                    return path.join(dir_name, fname)

        # no CBF file found, use raw folder
        return raw

    timestamp = path.getmtime(_find_path())
    return datetime.fromtimestamp(timestamp)
