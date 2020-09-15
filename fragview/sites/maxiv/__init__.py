from os import path
from datetime import datetime
from fragview.sites import plugin
from fragview.sites.plugin import Pipeline, LigandTool
from fragview.sites.maxiv.project import ProjectLayout
from fragview.sites.maxiv.diffractions import DiffractionImageMaker
from fragview.sites.maxiv.pipelines import PipelineCommands
from fragview.sites.maxiv.beamline import BeamlineInfo
from fragview.sites.maxiv.hpc import HPC


class SitePlugin(plugin.SitePlugin):
    NAME = "MAX IV Laboratory"
    LOGO = "maxiv.png"
    DISABLED_FEATURES = ["soaking_plan"]
    ACCOUNT_STYLE = "DUO"
    AUTH_BACKEND = "fragview.auth.ISPyBBackend"
    PROPOSALS_DIR = "/data/visitors/biomax"

    def get_project_experiment_date(self, project):
        # use main shift's date as somewhat random experiment data
        return datetime.strptime(project.shift, "%Y%m%d")

    def get_project_datasets(self, project):
        from fragview.projects import project_raw_master_h5_files

        for master_file in project_raw_master_h5_files(project):
            file_name = path.basename(master_file)
            # chopping of the '_master.h5' from the file name
            # gives us the data set name in the format we are using
            yield file_name[: -len("_master.h5")]

    def get_project_layout(self):
        return ProjectLayout()

    def get_diffraction_img_maker(self):
        return DiffractionImageMaker()

    def get_beamline_info(self):
        return BeamlineInfo()

    def get_hpc_runner(self):
        return HPC()

    def get_group_name(self, project):
        return f"{project.proposal}-group"

    def create_meta_files(self, project):
        return _copy_xmls_from_raw(project)

    def prepare_project_folders(self, project, shifts):
        from fragview.autoproc import import_autoproc

        import_autoproc(project, shifts)

    def get_supported_pipelines(self):
        return {
            Pipeline.AUTO_PROC,
            Pipeline.XIA2_DIALS,
            Pipeline.EDNA_PROC,
            Pipeline.FASTDP,
            Pipeline.XDSAPP,
            Pipeline.XIA2_XDS,
            Pipeline.DIMPLE,
            Pipeline.FSPIPELINE,
            Pipeline.BUSTER,
            Pipeline.RHO_FIT,
            Pipeline.LIGAND_FIT,
            Pipeline.PIPEDREAM_PROC,
            Pipeline.PIPEDREAM_REFINE,
            Pipeline.PIPEDREAM_LIGAND,
            Pipeline.PANDDA,
        }

    def get_supported_ligand_tools(self):
        return LigandTool.GRADE, {LigandTool.GRADE, LigandTool.ACEDRG, LigandTool.ELBOW}

    def get_pipeline_commands(self):
        return PipelineCommands()


def _copy_xmls_from_raw(project):
    from worker.xsdata import copy_collection_metadata_files
    from fragview.projects import project_xml_files

    xml_files = list(project_xml_files(project))
    copy_collection_metadata_files(project, xml_files)

    return xml_files
