import re
from fragview.sites import plugin


class ProjectLayout(plugin.ProjectLayout):
    ROOT_NAME = "Proposal Number"

    def root(self):
        return dict(name=self.ROOT_NAME, placeholder="20180489")

    def check_root(self, root):
        _is_8_digits(root, self.ROOT_NAME)

    def subdirs(self):
        return dict(name="Shifts", placeholder="20190622,20190629")

    def check_subdirs(self, subdirs):
        for sub_dir in subdirs.split(","):
            _is_8_digits(sub_dir, "shift")


def _is_8_digits(str, subject):
    if re.match("^\\d{8}$", str) is None:
        raise plugin.ProjectLayout.ValidationError(
            f"invalid {subject} '{str}', should be 8 digits"
        )
