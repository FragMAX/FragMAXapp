import re
from os import path
import subprocess
from datetime import datetime
from django.conf import settings
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


def _find_h5_file(proj, dataset, run, h5_data_num):
    from fragview.projects import project_shift_dirs

    for shift_dir in project_shift_dirs(proj):
        h5_file = path.join(shift_dir, "raw", proj.protein, dataset, f"{dataset}_{run}_data_{h5_data_num}.h5")
        if path.isfile(h5_file):
            return h5_file

    # H5 file not found
    raise DiffractionImageMaker.SourceImageNotFound()


class DiffractionImageMaker(plugin.DiffractionImageMaker):
    def get_file_names(self, project, dataset, run, image_num):
        h5_data_num = f"{image_num:06d}"
        h5_file = _find_h5_file(project, dataset, run, h5_data_num)
        jpeg_name = f"diffraction_{run}_{h5_data_num}.jpeg"

        return h5_file, jpeg_name

    def get_command(self, source_file, dest_pic_file):
        return ["adxv", "-sa", "-slabs", "10", "-weak_data", source_file, dest_pic_file]


class BeamlineInfo(plugin.BeamlineInfo):
    name = "BioMAX"
    detector_name = "EIGER 16M"
    detector_type = "Hybrid pixel direct counting device"
    detector_pixel_size = "0.075 mm x 0.075 mm"
    focusing_optics = "KB Mirrors"
    monochrom_type = "Si(111)"
    beam_divergence = "6 μrad x 104 μrad"
    polarisation = "0.99˚"


def _copy_xmls_from_raw(project):
    from worker.xsdata import copy_collection_metadata_files
    from fragview.projects import project_xml_files

    xml_files = list(project_xml_files(project))
    copy_collection_metadata_files(project, xml_files)

    return xml_files


class SitePlugin(plugin.SitePlugin):
    NAME = "MAX IV Laboratory"
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

    def get_diffraction_img_maker(self):
        return DiffractionImageMaker()

    def get_beamline_info(self):
        return BeamlineInfo()

    def get_hpc_runner(self):
        return HPC()

    def get_group_name(self, project):
        return f"{project.proposal}-group"

    def create_meta_files(self, project):
        return _copy_xmls_from_raw(project)

    def prepare_project_folders(self, project, shifts):
        from fragview.autoproc import import_autoproc
        import_autoproc(project, shifts)


def _ssh_on_frontend(command):
    """
    return a tuple of (stdout, stderr, exit_code)
    """
    print(f"running on HPC '{command}'")
    with subprocess.Popen(["ssh", settings.HPC_FRONT_END],
                          stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE) as proc:

        stdout, stderr = proc.communicate(command.encode("utf-8"))
        return stdout, stderr, proc.returncode


class HPC(plugin.HPC):
    def run_sbatch(self, sbatch_script, sbatch_options=None):
        cmd = "sbatch"

        # add options to sbatch command, if specified
        if sbatch_options is not None:
            cmd += f" {sbatch_options}"

        # add script for sbatch to run
        cmd += f" {sbatch_script}"

        # TODO: check exit code and bubble up error on exit code != 0
        _ssh_on_frontend(cmd)
