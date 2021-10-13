import re
from fragview.sites import plugin


class ProjectLayout(plugin.ProjectLayout):
    ROOT_NAME = "User Proposal"

    def root(self):
        return dict(name=self.ROOT_NAME, placeholder="frag200")

    def check_root(self, root):
        if re.match(r"^frag\d{3,6}$", root) is None:
            raise ProjectLayout.ValidationError(
                f"invalid {self.ROOT_NAME} '{root}', should be in the format fragNNN"
            )

    @staticmethod
    def subdirs():
        # no subdirectories used for plain data dirs layout
        return None

    @staticmethod
    def check_subdirs(subdirs):
        # no subdirectories used for plain data dirs layout
        pass
