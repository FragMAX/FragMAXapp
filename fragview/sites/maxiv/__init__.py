from os import path
from typing import List
from fragview.sites import plugin
from fragview.sites.plugin import Pipeline, LigandTool
from fragview.sites.maxiv.diffractions import get_diffraction_pic_command
from fragview.sites.maxiv.pipelines import PipelineCommands
from fragview.sites.maxiv.beamline import BeamlineInfo
from fragview.sites.maxiv.hpc import HPC


class SitePlugin(plugin.SitePlugin):
    NAME = "MAX IV Laboratory"
    LOGO = "maxiv.png"
    DISABLED_FEATURES = ["soaking_plan"]
    ACCOUNT_STYLE = "DUO"
    AUTH_BACKEND = "fragview.auth.ISPyBBackend"
    RAW_DATA_DIR = "/data/visitors/biomax"
    HPC_JOBS_RUNNER = "slurm"

    def get_project_datasets(self, project):
        from fragview.projects import project_raw_master_h5_files

        for master_file in project_raw_master_h5_files(project):
            file_name = path.basename(master_file)
            # chopping of the '_master.h5' from the file name
            # gives us the data set name in the format we are using
            yield file_name[: -len("_master.h5")]

    def get_diffraction_picture_command(
        self, project, dataset, angle: int, dest_pic_file
    ) -> List[str]:
        return get_diffraction_pic_command(project, dataset, angle, dest_pic_file)

    def get_beamline_info(self):
        return BeamlineInfo()

    def get_hpc_runner(self):
        return HPC()

    def get_group_name(self, project):
        return f"{project.proposal}-group"

    def prepare_project_folders(self, project, shifts):
        # NOP
        pass

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
            # TODO: disable pipedream for now
            # we need to test and potentially update
            # the code for running pipedream tools
            # Pipeline.PIPEDREAM_PROC,
            # Pipeline.PIPEDREAM_REFINE,
            # Pipeline.PIPEDREAM_LIGAND,
            Pipeline.PANDDA,
        }

    def get_supported_ligand_tools(self):
        return (
            LigandTool.GRADE,
            {
                LigandTool.GRADE,
                # disable AceDRG until issue #11 is resolved
                # LigandTool.ACEDRG,
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
