from typing import List
from os import path, walk
from datetime import datetime
from fragview.fileio import makedirs
from fragview.sites import plugin
from fragview.sites.plugin import Pipeline, LigandTool
from fragview.sites.hzb.diffractions import get_diffraction_pic_command
from fragview.sites.hzb.pipelines import PipelineCommands
from fragview.sites.hzb.beamline import BeamlineInfo
from fragview.sites.hzb.hpc import HPC

# filename suffix for a dataset's master image file
MASTER_IMG_SUFFIX = "_0001.cbf"


class SitePlugin(plugin.SitePlugin):
    NAME = "Helmholtz-Zentrum Berlin"
    LOGO = "hzb.png"
    DISABLED_FEATURES = ["soaking_plan"]
    AUTH_BACKEND = "fragview.auth.LocalBackend"
    RAW_DATA_DIR = "/data/fragmaxrpc/user"
    HPC_JOBS_RUNNER = "local"

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

    def prepare_project_folders(self, project, shifts):
        from fragview.projects import project_process_protein_dir

        root_dir = project_process_protein_dir(project)

        for dataset in self.get_project_datasets(project):
            dataset_dir, _ = dataset.rsplit("_", 2)
            makedirs(path.join(root_dir, dataset_dir, dataset))

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
        return (
            f"source /soft/pxsoft/64/ccp4/ccp4-6.5.0/ccp4-7.0/bin/ccp4.setup-csh; "
            f"cd {pandda_path}; pandda.inspect"
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
