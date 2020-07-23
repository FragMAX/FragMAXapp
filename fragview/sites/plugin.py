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
