from typing import Optional, Iterable
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class DatasetMetadata:
    detector: str
    resolution: float
    images: int
    start_time: datetime
    end_time: Optional[datetime]
    wavelength: float
    start_angle: float
    angle_increment: float
    exposure_time: float
    detector_distance: float
    xbeam: Optional[float]
    ybeam: Optional[float]
    beam_shape: str
    transmission: float
    slit_gap_horizontal: Optional[float]
    slit_gap_vertical: Optional[float]
    flux: float
    beam_size_at_sample_x: float
    beam_size_at_sample_y: float
    snapshot_indices: list[int] = field(default_factory=list)


class SitePlugin:
    NAME: str
    LOGO: str
    DISABLED_FEATURES: list[str] = []
    ACCOUNT_STYLE: Optional[str] = None
    AUTH_BACKEND: str
    # root path to where proposals data is stored
    RAW_DATA_DIR: str
    # runner used for HPC jobs,
    # should be either 'local' or 'slurm'
    HPC_JOBS_RUNNER: str

    def get_project_dir(self, project) -> Path:
        raise NotImplementedError()

    def get_project_dataset_dirs(self, project) -> Iterable[Path]:
        raise NotImplementedError()

    def get_dataset_runs(self, data_dir: Path) -> Iterable[int]:
        raise NotImplementedError()

    def get_dataset_metadata(
        self, project, dataset_dir: Path, crystal_id: str, run: int
    ) -> Optional[DatasetMetadata]:
        raise NotImplementedError()

    def get_dataset_master_image(self, project, dataset) -> Path:
        raise NotImplementedError()

    def add_pandda_init_commands(self, batch):
        """
        add site specific commands to prepare environment
        for running PanDDA commands
        """
        raise NotImplementedError()

    def get_diffraction_picture_command(
        self, project, dataset, angle: int, dest_pic_file
    ) -> list[str]:
        raise NotImplementedError()

    def get_beamline_info(self):
        raise NotImplementedError()

    def get_hpc_runner(self) -> "HPC":
        raise NotImplementedError()

    def get_group_name(self, project):
        """
        get the name of the filesystem group, which
        should own the files in the project's directory
        """
        raise NotImplementedError()

    def dataset_master_image(self, dataset):
        """
        return the file name of the master image for specified dataset
        """
        raise NotImplementedError()

    def get_supported_pipelines(self) -> set[str]:
        """
        return set of pipelines supported by this site,
        must be a set() of Pipeline class's fields
        """
        raise NotImplementedError()

    def get_supported_ligand_tools(self):
        """
        return set of ligand tools supported by this site,
        must be a set() of LigandTool class's fields
        """
        raise NotImplementedError()

    def get_pipeline_commands(self):
        raise NotImplementedError()

    def get_pandda_inspect_commands(self, pandda_path) -> str:
        """
        The shell commands for launching pandda inspect tool.
        We show this command to the user on the 'pandda analyse' page as
        instructions on how to run pandda inspect for a given analysis result.
        """
        raise NotImplementedError()


class Pipeline:
    AUTO_PROC = "auto_proc"
    XIA2_DIALS = "xia2_dials"
    EDNA_PROC = "edna_proc"
    XDSAPP = "xdsapp"
    XIA2_XDS = "xia2_xds"
    DIMPLE = "dimple"
    FSPIPELINE = "fspipeline"
    RHO_FIT = "rhofit"
    LIGAND_FIT = "ligandfit"
    PANDDA = "pandda"


class LigandTool:
    """
    tools that can convert ligand SMILES into PDB/CIF files
    """

    GRADE = "grade"
    ACEDRG = "acedrg"
    ELBOW = "elbow"


class BeamlineInfo:
    # beamline's name
    name: str
    detector_type: str
    detector_pixel_size: str
    focusing_optics: str
    monochrom_type: str
    beam_divergence: str
    polarisation: str


class PipelineCommands:
    def get_xia_dials_commands(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        raise NotImplementedError()

    def get_xia_xds_commands(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        raise NotImplementedError()

    def get_xdsapp_command(
        self, space_group, unit_cell, custom_parameters, friedel, image_file, num_images
    ):
        raise NotImplementedError()

    def get_autoproc_command(
        self,
        output_dir,
        space_group,
        unit_cell,
        custom_parameters,
        friedel,
        image_file,
        num_images,
    ):
        raise NotImplementedError()

    def get_dimple_command(self, dstmtz, custom_parameters):
        raise NotImplementedError()

    def get_fspipeline_commands(self, pdb, custom_parameters):
        raise NotImplementedError()

    def get_giant_datasets_cluster_command(self) -> str:
        raise NotImplementedError()


class HPC:
    def new_batch_file(self, job_name, script_name, stdout, stderr, cpus=None):
        """
        create new batch file, returns instance of BatchFile class
        """
        raise NotImplementedError()


class Duration:
    """
    represents a time duration
    """

    def __init__(
        self,
        hours: Optional[int] = None,
        minutes: Optional[int] = None,
        seconds: Optional[int] = None,
    ):
        def between_0_and_60(val):
            return 60 > val >= 0

        self.hours = 0
        self.minutes = 0
        self.seconds = 0

        if hours:
            assert hours > 0
            self.hours = hours

        if minutes:
            assert between_0_and_60(minutes)
            self.minutes = minutes

        if seconds:
            assert between_0_and_60(seconds)
            self.seconds = seconds

    def as_hms_text(self):
        return f"{self.hours:02}:{self.minutes:02}:{self.seconds:02}"


class DataSize:
    def __init__(
        self,
        gigabyte: Optional[int] = None,
        megabyte: Optional[int] = None,
        kilobyte: Optional[int] = None,
    ):
        def set_res(val, unit):
            if val is None:
                return res

            if res is not None:
                raise ValueError("multiple size units not supported")

            return val, unit

        res = None
        res = set_res(gigabyte, "G")
        res = set_res(megabyte, "M")
        res = set_res(kilobyte, "K")

        if res is None:
            raise ValueError("no size value specified")

        self.value, self.unit = res


class BatchFile:
    HEADER = "#!/bin/bash"

    def __init__(self, name, filename, stdout, stderr, cpus):
        self._name = name
        self._filename = filename
        self._stdout = stdout
        self._stderr = stderr
        self._body = f"{self.HEADER}\n"
        # expected number of CPU this task will use
        self._cpus = cpus

    def set_options(
        self,
        time: Optional[Duration] = None,
        exclusive=None,
        nodes=None,
        partition=None,
        mem_per_cpu: Optional[DataSize] = None,
        memory: Optional[DataSize] = None,
    ):
        """
        time - a limit on the total run time of the batch file
        exclusive - don't share compute node with this job
        nodes - minimum of nodes be allocated to this job
        mem_per_cpu - minimum memory required per allocated CPU
        partition - specific partition for the resource allocation
        memory - memory required to run this job, in gigabytes
        """
        raise NotImplementedError()

    def save(self):
        from fragview.fileio import write_script

        write_script(self._filename, self._body)

    def assign_variable(self, var_name, expression):
        raise NotImplementedError()

    def load_python_env(self):
        """
        add commands to activate python environment
        """
        raise NotImplementedError()

    def load_modules(self, modules):
        """
        add command to load specified lmod modules

        modules - a list of module names to load
        """
        raise NotImplementedError()

    def purge_modules(self):
        """
        add command to purge (unload) lmod modules from the environment
        """
        raise NotImplementedError()

    def add_line(self, line):
        self._body += f"{line}\n"

    def add_command(self, cmd):
        self.add_line(cmd)

    def add_commands(self, *cmds):
        for cmd in cmds:
            self.add_command(cmd)
