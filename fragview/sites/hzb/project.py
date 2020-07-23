import re
from fragview.sites import plugin


class ProjectLayout(plugin.ProjectLayout):
    ROOT_NAME = "User Proposal"

    def root(self):
        return dict(name=self.ROOT_NAME, placeholder="frag200000")

    def check_root(self, root):
        if re.match(r"^frag\d{6}$", root) is None:
            raise ProjectLayout.ValidationError(
                f"invalid {self.ROOT_NAME} '{root}', should be in the format frag20000"
            )

    @staticmethod
    def subdirs():
        # no subdirectories used for plain data dirs layout
        return None

    @staticmethod
    def check_subdirs(subdirs):
        # no subdirectories used for plain data dirs layout
        pass
