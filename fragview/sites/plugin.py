class SitePlugin:
    NAME = None
    LOGO = None
    DISABLED_FEATURES = []
    ACCOUNT_STYLE = None
    AUTH_BACKEND = None
    PROPOSALS_DIR = None  # root path to where proposals data is stored

    def get_project_experiment_date(self, project):
        raise NotImplementedError()

    def get_project_datasets(self, project):
        raise NotImplementedError()

    def get_project_layout(self):
        raise NotImplementedError()

    def get_diffraction_img_maker(self):
        raise NotImplementedError()

    def get_beamline_info(self):
        raise NotImplementedError()

    def get_hpc_runner(self):
        raise NotImplementedError()

    def get_group_name(self, project):
        """
        get the name of the filesystem group, which
        should own the files in the project's directory
        """
        raise NotImplementedError()

    def create_meta_files(self, project):
        raise NotImplementedError()

    def prepare_project_folders(self, project, shifts):
        raise NotImplementedError()

    def get_supported_pipelines(self):
        """
        return set of pipelines supported by this site,
        must be a set() of Pipeline class's fields
        """
        raise NotImplementedError()

    def get_supported_ligand_tools(self):
        """
        return set of ligand tools supported by this site,
        must be a set() of LigandTool class's fields
        """
        raise NotImplementedError()

    def get_pipeline_commands(self):
        raise NotImplementedError()


class Pipeline:
    AUTO_PROC = "auto_proc"
    XIA2_DIALS = "xia2_dials"
    EDNA_PROC = "edna_proc"
    FASTDP = "fastdp"
    XDSAPP = "xdsapp"
    XIA2_XDS = "xia2_xds"
    DIMPLE = "dimple"
    FSPIPELINE = "fspipeline"
    BUSTER = "buster"
    RHO_FIT = "rho_fit"
    LIGAND_FIT = "ligand_fit"
    PIPEDREAM_PROC = "pipedream_proc"
    PIPEDREAM_REFINE = "pipedream_refine"
    PIPEDREAM_LIGAND = "pipedream_ligand"
    PANDDA = "pandda"


class LigandTool:
    """
    tools that can convert ligand SMILES into PDB/CIF files
    """
    GRADE = "grade"
    ACEDRG = "acedrg"
    ELBOW = "elbow"


class ProjectLayout:
    class ValidationError(Exception):
        def __init__(self, message):
            super().__init__(message)

    def root(self):
        raise NotImplementedError()

    def check_root(self, root):
        raise NotImplementedError()

    def subdirs(self):
        raise NotImplementedError()

    def check_subdirs(self, subdirs):
        raise NotImplementedError()


class DiffractionImageMaker:
    class SourceImageNotFound(Exception):
        pass

    def get_file_names(self, project, dataset, run, image_num):
        """
        return tuple of (source_file, pic_file_name)

        where:
          source_file - is the full path to use as source file for generating the diffraction picture
          pic_file_name - the picture file name to use
        """
        raise NotImplementedError()

    def get_command(self, source_file, dest_pic_file):
        """
        return command to create diffraction picture from the source file
        """
        raise NotImplementedError()


class BeamlineInfo:
    # beamline's name
    name = None
    detector_type = None
    detector_model = None
    detector_pixel_size = None
    focusing_optics = None
    monochrom_type = None
    beam_divergence = None
    polarisation = None


class HPC:
    def run_batch(self, sbatch_script, sbatch_options=None):
        raise NotImplementedError()

    def new_batch_file(self, script_name):
        """
        create new batch file, returns instance of BatchFile class
        """
        raise NotImplementedError()


class BatchFile:
    HEADER = "#!/bin/bash"

    def __init__(self, filename):
        self._filename = filename
        self._body = f"{self.HEADER}\n"

    def save(self):
        from fragview.fileio import write_script
        write_script(self._filename, self._body)

    def load_python_env(self):
        raise NotImplementedError()

    def add_command(self, cmd):
        self._body += f"{cmd}\n"
