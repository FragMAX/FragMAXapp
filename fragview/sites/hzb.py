import re
from glob import glob
from os import path, walk
from datetime import datetime
from fragview.sites import plugin
from fragview.fileio import makedirs


class ProjectLayout(plugin.ProjectLayout):
    ROOT_NAME = "User Proposal"

    def root(self):
        return dict(name=self.ROOT_NAME, placeholder="frag200000")

    def check_root(self, root):
        if re.match(r"^frag\d{6}$", root) is None:
            raise ProjectLayout.ValidationError(
                f"invalid {self.ROOT_NAME} '{root}', should be in the format frag20000")

    @staticmethod
    def subdirs():
        # no subdirectories used for plain data dirs layout
        return None

    @staticmethod
    def check_subdirs(subdirs):
        # no subdirectories used for plain data dirs layout
        pass


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
    """
    list the data sets by looking at existing *.cbf files in
    subdirectories under the 'raw' folder
    """
    def _run_exists(set_dir, set_name, run):
        for n in range(1, 10):
            file_name = f"{set_name}_{run}_{n:04}.cbf"
            if path.isfile(path.join(set_dir, file_name)):
                return True

        return False

    def _sets(set_dir):
        """
        list all runs of a particular dataset by probing
        the *.cbf file names
        """
        run = 1
        set_name = path.basename(set_dir)
        while _run_exists(set_dir, set_name, run):
            yield f"{set_name}_{run}"
            run += 1

    from fragview.projects import project_raw_protein_dir
    raw = project_raw_protein_dir(project)

    for dir_name in glob(f"{raw}/*"):
        # list all datasets for each folder under 'raw'
        for set_name in _sets(dir_name):
            yield set_name


class SitePlugin(plugin.SitePlugin):
    LOGO = "hzb.png"

    FEATURES_DISABLED = [
        "soaking_plan",
        "pipedream",
        "download"
    ]

    AUTH_BACKEND = "fragview.auth.LocalBackend"

    PROPOSALS_DIR = "/data/fragmaxrpc/user"

    def get_project_experiment_date(self, project):
        return _get_experiment_timestamp(project)

    def get_project_datasets(self, project):
        return _get_datasets(project)

    def get_project_layout(self):
        return ProjectLayout()

    def get_group_name(self, project):
        return "fragadm"

    def create_meta_files(self, project):
        from fragview.cbf import generate_meta_xml_files
        return list(generate_meta_xml_files(project))

    def prepare_project_folders(self, project, shifts):
        from fragview.projects import project_process_protein_dir
        root_dir = project_process_protein_dir(project)

        for dataset in self.get_project_datasets(project):
            dataset_dir, _ = dataset.rsplit("_", 2)
            makedirs(path.join(root_dir, dataset_dir, dataset))
