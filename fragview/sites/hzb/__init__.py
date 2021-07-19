from os import path, walk
from pathlib import Path
from datetime import datetime
from fragview.fileio import subdirs
from fragview.fileio import makedirs
from fragview.sites import plugin
from fragview.sites.plugin import Pipeline, LigandTool
from fragview.sites.hzb.project import ProjectLayout
from fragview.sites.hzb.diffractions import get_diffraction_pic_command
from fragview.sites.hzb.pipelines import PipelineCommands
from fragview.sites.hzb.beamline import BeamlineInfo
from fragview.sites.hzb.hpc import HPC

# filename suffix for a dataset's master image file
MASTER_IMG_SUFFIX = "_0001.cbf"


class SitePlugin(plugin.SitePlugin):
    NAME = "Helmholtz-Zentrum Berlin"
    LOGO = "hzb.png"
    DISABLED_FEATURES = ["soaking_plan", "download"]
    AUTH_BACKEND = "fragview.auth.LocalBackend"
    RAW_DATA_DIR = "/data/fragmaxrpc/user"
    HPC_JOBS_RUNNER = "local"

    def get_project_experiment_date(self, project):
        return _get_experiment_timestamp(project)

    def get_project_datasets(self, project):
        return _get_datasets(project)

    def get_project_layout(self):
        return ProjectLayout()

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

    def create_meta_files(self, project):
        from fragview.cbf import generate_meta_xml_files

        return list(generate_meta_xml_files(project))

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


def _get_datasets(project):
    def _file_to_dataset_name(file):
        # to get dataset name, chop off the
        # _0001.cbf suffix
        return file.name[: -len(MASTER_IMG_SUFFIX)]

    from fragview.projects import project_raw_protein_dir

    #
    # for each subdirectory in 'raw' directory,
    # look for dataset master image files, i.e. files
    # with names like <protein>..._0001.cbf,
    # derive dataset name from master image file name
    #

    raw = Path(project_raw_protein_dir(project))
    glob_exp = f"{project.protein}*{MASTER_IMG_SUFFIX}"

    for dset_dir in subdirs(raw, 1):
        for img_file in dset_dir.glob(glob_exp):
            yield _file_to_dataset_name(img_file)
