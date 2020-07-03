import re
from os import path, walk
from datetime import datetime
from fragmax import sites
from fragview.projects import project_raw_protein_dir


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
    def get_experiment_date(project):
        # use main shift's date as somewhat random experiment data
        return datetime.strptime(project.shift, "%Y%m%d")


def _get_cbf_experiment_timestamp(project):
    def _find_path():
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
