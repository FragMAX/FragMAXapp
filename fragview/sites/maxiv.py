import re
from os import path
from datetime import datetime
from fragview.sites import plugin


def _is_8_digits(str, subject):
    if re.match("^\\d{8}$", str) is None:
        raise plugin.ProjectLayout.ValidationError(f"invalid {subject} '{str}', should be 8 digits")


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


def _copy_xmls_from_raw(project):
    from worker.xsdata import copy_collection_metadata_files
    from fragview.projects import project_xml_files

    xml_files = list(project_xml_files(project))
    copy_collection_metadata_files(project, xml_files)

    return xml_files


class SitePlugin(plugin.SitePlugin):
    LOGO = "maxiv.png"
    DISABLED_FEATURES = ["soaking_plan"]
    ACCOUNT_STYLE = "DUO"
    AUTH_BACKEND = "fragview.auth.ISPyBBackend"
    PROPOSALS_DIR = "/data/visitors/biomax"

    def get_project_experiment_date(self, project):
        # use main shift's date as somewhat random experiment data
        return datetime.strptime(project.shift, "%Y%m%d")

    def get_project_datasets(self, project):
        from fragview.projects import project_raw_master_h5_files
        for master_file in project_raw_master_h5_files(project):
            file_name = path.basename(master_file)
            # chopping of the '_master.h5' from the file name
            # gives us the data set name in the format we are using
            yield file_name[:-len("_master.h5")]

    def get_project_layout(self):
        return ProjectLayout()

    def get_group_name(self, project):
        return f"{project.proposal}-group"

    def create_meta_files(self, project):
        return _copy_xmls_from_raw(project)

    def prepare_project_folders(self, project, shifts):
        from fragview.autoproc import import_autoproc
        import_autoproc(project, shifts)
