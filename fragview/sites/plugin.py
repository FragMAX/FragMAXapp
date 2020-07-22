class SitePlugin:
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
