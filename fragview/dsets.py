from pathlib import PosixPath
from fragview.fileio import read_csv_lines
from fragview.projects import project_data_collections_file, project_all_status_file


class DataSet:
    ISPYB_STORAGE = PosixPath("/mxn/groups/ispybstorage")

    def __init__(
        self, image_prefix, sample_name, data_path, acronym, run, num_images, resolution, snapshot, status,
    ):
        self.image_prefix = image_prefix
        self.sample_name = sample_name
        self.data_path = data_path
        self.acronym = acronym
        self.run = run
        self.num_images = num_images
        self.resolution = resolution
        self.snapshot = snapshot
        self.status = status

        self._snapshots = None

    def is_apo(self):
        return self.sample_name.startswith("Apo")

    def _get_snapshots(self):
        def _rel(abs_path):
            return str(PosixPath(abs_path).relative_to(self.ISPYB_STORAGE))

        # no snapshot available
        if self.snapshot == "noSnapshots":
            return None, None

        # two snapshots available
        if "," in self.snapshot:
            s1, s2 = self.snapshot.split(",")
            return _rel(s1), _rel(s2)

        # only one snapshot
        return _rel(self.snapshot), None

    def snapshots(self):
        if self._snapshots is None:
            self._snapshots = self._get_snapshots()

        return self._snapshots


class DataSetStatus:
    def __init__(
        self,
        auto_proc="unknown",
        xia2_dials="unknown",
        edna_proc="unknown",
        fastdp="unknown",
        xdsapp="unknown",
        xia2_xds="unknown",
        dimple="unknown",
        fspipeline="unknown",
        buster="unknown",
        rho_fit="unknown",
        ligand_fit="unknown",
        pipedream_proc="unknown",
        pipedream_refine="unknown",
        pipedream_ligand="unknown",
    ):

        self.auto_proc = auto_proc
        self.xia2_dials = xia2_dials
        self.edna_proc = edna_proc
        self.fastdp = fastdp
        self.xdsapp = xdsapp
        self.xia2_xds = xia2_xds
        self.dimple = dimple
        self.fspipeline = fspipeline
        self.buster = buster
        self.rho_fit = rho_fit
        self.ligand_fit = ligand_fit
        self.pipedream_proc = pipedream_proc
        self.pipedream_refine = pipedream_refine
        self.pipedream_ligand = pipedream_ligand


def _status_from_string(stat):
    if stat == "full":
        return "success"

    if stat == "partial":
        return "failure"

    return "unknown"


def _load_datasets_status(proj):
    status = {}

    for line in read_csv_lines(project_all_status_file(proj)):
        name, *proc_stats = line
        proc_status = [_status_from_string(s) for s in proc_stats]

        status[name] = DataSetStatus(*proc_status)

    return status


def get_datasets(proj):
    ds_status = _load_datasets_status(proj)
    lines = read_csv_lines(project_data_collections_file(proj))

    unknown_status = DataSetStatus()

    # skip header
    lines = lines[1:]

    for line in lines:
        ds_name = f"{line[0]}_{line[4]}"

        status = ds_status[ds_name] if ds_name in ds_status else unknown_status

        yield DataSet(
            line[0], line[1], line[2], line[3], line[4], line[5], line[6], line[7], status,
        )