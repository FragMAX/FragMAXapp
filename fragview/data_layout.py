import re
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
