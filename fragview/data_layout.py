import re
from glob import glob
from os import path, walk
from datetime import datetime
from fragmax import sites


class ValidationError(Exception):
    def __init__(self, message):
        super().__init__(message)


def _is_8_digits(str, subject):
    if re.match("^\\d{8}$", str) is None:
        raise ValidationError(f"invalid {subject} '{str}', should be 8 digits")


class ShiftsDirsLayout:
    ROOT_NAME = "Proposal Number"

    def root(self):
        return dict(name=self.ROOT_NAME, placeholder="20180489")

    def check_root(self, root):
        _is_8_digits(root, self.ROOT_NAME)

    @staticmethod
    def subdirs():
        return dict(name="Shifts", placeholder="20190622,20190629")

    def check_subdirs(self, subdirs):
        for sub_dir in subdirs.split(","):
            _is_8_digits(sub_dir, "shift")

    @staticmethod
    def get_group_name(proposal):
        return f"{proposal}-group"

    @staticmethod
    def get_project_datasets(project):
        from fragview.projects import project_raw_master_h5_files
        for master_file in project_raw_master_h5_files(project):
            file_name = path.basename(master_file)
            # chopping of the '_master.h5' from the file name
            # gives us the data set name in the format we are using
            yield file_name[:-len("_master.h5")]

    @staticmethod
    def get_experiment_date(project):
        # use main shift's date as somewhat random experiment data
        return datetime.strptime(project.shift, "%Y%m%d")


def _get_cbf_experiment_timestamp(project):
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


def _get_cbf_datasets(project):
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


class PlainDirLayout:
    ROOT_NAME = "User Proposal"

    def root(self):
        return dict(name=self.ROOT_NAME, placeholder="frag200000")

    def check_root(self, root):
        if re.match(r"^frag\d{6}$", root) is None:
            raise ValidationError(f"invalid {self.ROOT_NAME} '{root}', should be in the format frag20000")

    @staticmethod
    def subdirs():
        # no subdirectories used for plain data dirs layout
        return None

    @staticmethod
    def check_subdirs(subdirs):
        # no subdirectories used for plain data dirs layout
        pass

    @staticmethod
    def get_group_name(_):
        return "fragadm"

    @staticmethod
    def get_experiment_date(project):
        return _get_cbf_experiment_timestamp(project)

    @staticmethod
    def get_project_datasets(project):
        return _get_cbf_datasets(project)


_STYLE_CLS = {
    "shifts": ShiftsDirsLayout,
    "plain": PlainDirLayout,
}


def get_layout():
    """
    Get the object for the configured data layout
    """
    style = sites.params().DATA_LAYOUT
    return _STYLE_CLS[style]()


def get_group_name(proposal):
    return get_layout().get_group_name(proposal)


def get_project_experiment_date(project):
    return get_layout().get_experiment_date(project)
